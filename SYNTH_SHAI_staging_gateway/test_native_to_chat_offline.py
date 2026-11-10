"""Offline synthetic Google -> SHAI session -> /chat -> logout integration.

Uses in-process WSGI authentication, loopback HTTP chat, generated test keys,
an operator-provisioned temporary SQLite file, and an injected fake provider.
Never calls Google, OpenAI, Cloud Run, or a public endpoint. Not deployment proof.
144 HOLD: no live login, billing, child users, tools, or external actions.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib import error, request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from SYNTH_SHAI_staging_gateway.google_jwks_rotation import GOOGLE_JWKS_URI, GoogleJwksCache
from SYNTH_SHAI_staging_gateway.google_login_challenge import initialize_challenge_store
from SYNTH_SHAI_staging_gateway.native_google_exchange import NativeExchange, segment
from SYNTH_SHAI_staging_gateway.openai_chat_gateway import SlidingWindowLimiter, make_handler
from SYNTH_SHAI_staging_gateway.pilot_security import (
    initialize_store, reserve_request, verify_session_token,
)
from SYNTH_SHAI_staging_gateway.test_google_jwks_rotation import CLIENT, b64, jwk, payload


class NativeToChatOfflineTests(unittest.TestCase):
    """Composed contract test, not HTTPS/Cloud Run or production identity proof."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db_path = str(Path(temp.name) / "test.sqlite")
        initialize_store(self.db_path)
        initialize_challenge_store(self.db_path)

        self.shai_signer = ed25519.Ed25519PrivateKey.generate()
        public = self.shai_signer.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        self.enterContext(patch.dict(os.environ, {
            "SHAI_GATEWAY_DB": self.db_path,
            "SHAI_SESSION_ISSUER": "https://shai.invalid",
            "SHAI_SESSION_AUDIENCE": "test-service",
            "SHAI_SESSION_PUBLIC_KEY_HEX": public.hex(),
            "SHAI_PILOT_ENABLED": "1",
            "SHAI_PILOT_DEADLINE_UTC": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "OPENAI_API_KEY": "synthetic-server-only-placeholder",
        }))

        self.google_signer = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        self.cache = GoogleJwksCache()
        self.cache.install_trusted_response(
            payload(jwk(self.google_signer, "synthetic-kid")),
            "max-age=300", GOOGLE_JWKS_URI,
        )
        self.auth = NativeExchange(
            host="shai.invalid", client=CLIENT, android_client=None,
            allowed_subjects=["allowed-synthetic-sub"], store=self.db_path,
            cache=self.cache, signer=self.shai_signer,
            limiter=lambda addr, route: addr == "127.0.0.1",
        )
        self.provider_calls = []

        def fake_provider(server_key, message):
            self.provider_calls.append((server_key, message))
            return "offline-reply: " + message

        self.chat_server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            make_handler(
                send_to_openai=fake_provider,
                limiter=SlidingWindowLimiter(limit=50),
                authenticate=verify_session_token,
                reserve=reserve_request,
            ),
        )
        self.chat_thread = threading.Thread(
            target=self.chat_server.serve_forever, daemon=True
        )
        self.chat_thread.start()
        self.addCleanup(self._stop_chat_server)
        self.chat_url = "http://127.0.0.1:%d/chat" % self.chat_server.server_port

    def _stop_chat_server(self):
        self.chat_server.shutdown()
        self.chat_server.server_close()
        self.chat_thread.join(timeout=3)

    def auth_request(self, route, body, **overrides):
        raw = json.dumps(body).encode("utf-8")
        env = {
            "wsgi.url_scheme": "https",
            "HTTP_HOST": "shai.invalid",
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(raw)),
            "PATH_INFO": "/auth/" + route,
            "wsgi.input": io.BytesIO(raw),
            "REMOTE_ADDR": "127.0.0.1",
        }
        status_line = []
        wire = b"".join(self.auth(
            dict(env, **overrides),
            lambda status, headers: status_line.append(status),
        ))
        return int(status_line[0][:3]), json.loads(wire) if wire else None

    def chat(self, token, message="Hello"):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        req = request.Request(
            self.chat_url, data=json.dumps({"message": message}).encode(),
            headers=headers, method="POST",
        )
        try:
            with request.urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except error.HTTPError as exc:
            with exc:
                return exc.code, json.load(exc)

    def google_exchange_body(self, *, sub="allowed-synthetic-sub",
                             claim_overrides=None, signing_key=None):
        code, challenge = self.auth_request(
            "challenge", {"flow": "google-id-token-v1", "platform": "android"}
        )
        self.assertEqual(code, 201)
        now = int(time.time())
        claims = {
            "nonce": challenge["nonce"],
            "sub": sub,
            "iat": now,
            "exp": now + 300,
            "iss": "https://accounts.google.com",
            "aud": CLIENT,
        }
        if claim_overrides:
            claims.update(claim_overrides)
        signed = segment({"kid": "synthetic-kid", "alg": "RS256"}) + "." + segment(claims)
        key = signing_key if signing_key is not None else self.google_signer
        token = signed + "." + b64(key.sign(
            signed.encode("ascii"), padding.PKCS1v15(), hashes.SHA256()
        ))
        return {
            "challenge_id": challenge["challenge_id"],
            "completion_token": challenge["completion_token"],
            "google_id_token": token,
        }

    def login(self):
        code, payload = self.auth_request("google", self.google_exchange_body())
        self.assertEqual(code, 200)
        token = payload["access_token"]
        self.assertIsNotNone(verify_session_token(token))
        return token

    def test_valid_composed_flow_and_logout_revoke(self):
        body = self.google_exchange_body()
        self.assertEqual(self.chat(body["google_id_token"])[0], 401)
        self.assertEqual(self.chat(None)[0], 401)
        code, response = self.auth_request("google", body)
        self.assertEqual(code, 200)
        token = response["access_token"]
        self.assertIsNotNone(verify_session_token(token))
        self.assertEqual(
            self.chat(token, "Test lesson"),
            (200, {"reply": "offline-reply: Test lesson"}),
        )
        self.assertEqual(
            self.auth_request(
                "logout", {}, HTTP_AUTHORIZATION="Bearer " + token
            )[0], 204
        )
        self.assertEqual(self.chat(token)[0], 401)
        self.assertEqual(
            self.provider_calls,
            [("synthetic-server-only-placeholder", "Test lesson")],
        )

    def test_consumed_challenge_replay_never_mints_new_session(self):
        body = self.google_exchange_body()
        self.assertEqual(self.auth_request("google", body)[0], 200)
        self.assertEqual(self.auth_request("google", body)[0], 401)
        self.assertEqual(self.provider_calls, [])

    def test_google_claims_and_account_allowlist_fail_closed(self):
        variants = (
            {"sub": "not-allowlisted"},
            {"aud": "other.apps.googleusercontent.com"},
            {"iss": "https://impostor.invalid"},
            {"azp": "unapproved.apps.googleusercontent.com"},
            {"nonce": "z" * 43},
        )
        for changes in variants:
            with self.subTest(changes=changes):
                body = self.google_exchange_body(
                    sub=changes.get("sub", "allowed-synthetic-sub"),
                    claim_overrides=changes,
                )
                self.assertEqual(self.auth_request("google", body)[0], 401)
                self.assertEqual(self.auth_request("google", body)[0], 401)
        self.assertEqual(self.provider_calls, [])

    def test_forged_google_signature_cannot_issue_chat_session(self):
        impostor = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        body = self.google_exchange_body(signing_key=impostor)
        self.assertEqual(self.auth_request("google", body)[0], 401)
        self.assertEqual(self.provider_calls, [])

    def test_one_use_challenge_is_atomic_under_concurrent_callbacks(self):
        body = self.google_exchange_body()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda _: self.auth_request("google", body)[0], range(2)
            ))
        self.assertEqual(sorted(results), [200, 401])
        self.assertEqual(self.provider_calls, [])

    def test_untrusted_forwarded_https_and_host_stay_denied(self):
        body = {"flow": "google-id-token-v1", "platform": "android"}
        self.assertEqual(self.auth_request(
            "challenge", body, **{
                "wsgi.url_scheme": "http", "HTTP_X_FORWARDED_PROTO": "https",
            }
        )[0], 400)
        self.assertEqual(self.auth_request(
            "challenge", body, **{
                "HTTP_HOST": "attacker.invalid", "HTTP_X_FORWARDED_PROTO": "https",
            }
        )[0], 400)
        self.assertEqual(self.provider_calls, [])

    def test_missing_shared_quota_table_blocks_provider(self):
        token = self.login()
        with sqlite3.connect(self.db_path) as db:
            db.execute("DROP TABLE accepted")
        self.assertEqual(self.chat(token)[0], 503)
        self.assertEqual(self.provider_calls, [])

    def test_pilot_switch_off_blocks_signed_session(self):
        token = self.login()
        with patch.dict(os.environ, {"SHAI_PILOT_ENABLED": "0"}):
            self.assertEqual(self.chat(token)[0], 503)
        self.assertEqual(self.provider_calls, [])

    def test_real_quota_and_session_expiration_contract(self):
        token = self.login()
        self.assertIsNone(verify_session_token(token, now=time.time() + 901))
        for i in range(3):
            self.assertEqual(self.chat(token, "bounded-%d" % i)[0], 200)
        self.assertEqual(self.chat(token, "fourth")[0], 429)
        self.assertEqual(len(self.provider_calls), 3)


if __name__ == "__main__":
    unittest.main()
