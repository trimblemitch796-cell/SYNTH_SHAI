"""Exercise the native staging wire contract in process with temporary signing keys."""
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from SYNTH_SHAI_staging_gateway.google_jwks_rotation import GoogleJwksCache, GOOGLE_JWKS_URI
from SYNTH_SHAI_staging_gateway.google_login_challenge import initialize_challenge_store
from SYNTH_SHAI_staging_gateway.native_google_exchange import NativeExchange, segment
from SYNTH_SHAI_staging_gateway.pilot_security import initialize_store, reserve_request, verify_session_token
from SYNTH_SHAI_staging_gateway.test_google_jwks_rotation import CLIENT, b64, jwk, payload


class NativeExchangeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = str(Path(temp.name) / "test.sqlite")
        initialize_store(path)
        initialize_challenge_store(path)
        signer = ed25519.Ed25519PrivateKey.generate()
        public = signer.public_key().public_bytes(serialization.Encoding.Raw,
                                                  serialization.PublicFormat.Raw)
        self.enterContext(patch.dict(os.environ, SHAI_GATEWAY_DB=path,
                                     SHAI_SESSION_ISSUER="https://shai.invalid",
                                     SHAI_SESSION_AUDIENCE="test-service",
                                     SHAI_SESSION_PUBLIC_KEY_HEX=public.hex()))
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cache = GoogleJwksCache()
        cache.install_trusted_response(payload(jwk(self.key, "test")), "max-age=300", GOOGLE_JWKS_URI)
        self.app = NativeExchange(host="shai.invalid", client=CLIENT, android_client=None,
                                  allowed_subjects=["fixture"], store=path, cache=cache, signer=signer,
                                  limiter=lambda addr, route: addr == "127.0.0.1")

    def request(self, route, body, **overrides):
        raw = json.dumps(body).encode()
        env = {"wsgi.url_scheme": "https", "HTTP_HOST": "shai.invalid", "REQUEST_METHOD": "POST",
               "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(raw)),
               "PATH_INFO": "/auth/" + route, "wsgi.input": io.BytesIO(raw), "REMOTE_ADDR": "127.0.0.1"}
        result = []
        data = b"".join(self.app(dict(env, **overrides), lambda status, headers: result.append(status)))
        return int(result[0][:3]), json.loads(data) if data else None

    def completion(self, sub="fixture"):
        status, challenge = self.request("challenge", {"flow": "google-id-token-v1", "platform": "android"})
        self.assertEqual(status, 201)
        now = int(time.time())
        claims = {"nonce": challenge["nonce"], "sub": sub, "iat": now, "exp": now + 300,
                  "iss": "https://accounts.google.com", "aud": CLIENT}
        signed = segment({"kid": "test", "alg": "RS256"}) + "." + segment(claims)
        token = signed + "." + b64(self.key.sign(signed.encode(), padding.PKCS1v15(), hashes.SHA256()))
        return {"challenge_id": challenge["challenge_id"], "completion_token": challenge["completion_token"],
                "google_id_token": token}

    def test_issue_replay_and_revoke(self):
        body = self.completion()
        status, session = self.request("google", body)
        self.assertEqual(status, 200)
        self.assertEqual(self.request("google", body)[0], 401)
        token = session["access_token"]
        identity = verify_session_token(token)
        self.assertIsNotNone(identity)
        self.assertEqual(self.request("logout", {}, HTTP_AUTHORIZATION="Bearer " + token)[0], 204)
        self.assertEqual(reserve_request(identity), "revoked")

    def test_wrong_bearer_burns_attempt(self):
        body = self.completion()
        self.assertEqual(self.request("google", dict(body, completion_token="x" * 43))[0], 401)
        self.assertEqual(self.request("google", body)[0], 401)

    def test_other_account_denied(self):
        self.assertEqual(self.request("google", self.completion("another-user"))[0], 401)

    def test_reject_wire_and_rate_errors(self):
        for change, status in [({"wsgi.url_scheme": "http"}, 400), ({"HTTP_HOST": "other"}, 400),
                               ({"REMOTE_ADDR": "other"}, 429), ({"CONTENT_LENGTH": "18000"}, 400)]:
            self.assertEqual(self.request("challenge", {}, **change)[0], status)


    def test_cloud_run_forwarded_https_header_does_not_override_http_wsgi_scheme(self):
        # Cloud Run terminates TLS upstream of the container. A caller-controlled
        # X-Forwarded-Proto value alone must never promote this request to HTTPS.
        status, response = self.request(
            "challenge", {"flow": "google-id-token-v1", "platform": "android"},
            **{"wsgi.url_scheme": "http", "HTTP_X_FORWARDED_PROTO": "https"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(response, {})

    def test_cloud_run_untrusted_host_still_denied_with_forwarded_https(self):
        status, response = self.request(
            "challenge", {"flow": "google-id-token-v1", "platform": "android"},
            **{"HTTP_HOST": "attacker.invalid", "HTTP_X_FORWARDED_PROTO": "https"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(response, {})

    def test_no_trusted_jwks_fails_closed_and_burns_challenge(self):
        body = self.completion()
        self.app.cache = GoogleJwksCache()  # no keys; must not fetch during request
        self.assertEqual(self.request("google", body)[0], 401)
        self.assertEqual(self.request("google", body)[0], 401)

    def test_unavailable_challenge_store_fails_closed(self):
        self.app.store = "/this-path-is-not-provisioned/shai-staging.sqlite"
        status, response = self.request(
            "challenge", {"flow": "google-id-token-v1", "platform": "android"}
        )
        self.assertEqual(status, 503)
        self.assertEqual(response, {})

    def test_unavailable_limiter_fails_closed(self):
        with patch.object(self.app, "limiter", side_effect=RuntimeError("limiter offline")):
            status, response = self.request(
                "challenge", {"flow": "google-id-token-v1", "platform": "android"}
            )
        self.assertEqual(status, 503)
        self.assertEqual(response, {})
