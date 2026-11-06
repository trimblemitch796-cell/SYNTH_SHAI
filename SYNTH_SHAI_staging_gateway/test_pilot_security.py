"""Offline signed-session and quota tests; no hosted identity service or AI calls."""
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from SYNTH_SHAI_staging_gateway import pilot_security as s


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


class SessionSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / "pilot.sqlite")
        s.initialize_store(self.path)
        self.private = Ed25519PrivateKey.generate()
        pub = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.settings = patch.dict(os.environ, {
            "SHAI_SESSION_ISSUER": "https://trusted.example.invalid",
            "SHAI_SESSION_AUDIENCE": "shai-staging",
            "SHAI_SESSION_PUBLIC_KEY_HEX": pub.hex(),
            "SHAI_GATEWAY_DB": self.path,
        })
        self.settings.start()
        self.addCleanup(self.settings.stop)

    def token(self, **updates):
        claims = dict(iss_="https://trusted.example.invalid")
        claims = {"iss": claims["iss_"], "aud": "shai-staging",
                  "sub": "user-1", "jti": "nonce-revocable-12345",
                  "iat": 1000, "nbf": 1000, "exp": 1900}
        claims.update(updates)
        header = b64(json.dumps({"alg":"EdDSA","typ":"JWT"}, separators=(",", ":")).encode())
        content = b64(json.dumps(claims, separators=(",", ":")).encode())
        signature = self.private.sign((header+"."+content).encode())
        return header+"."+content+"."+b64(signature)

    def test_good_token_and_single_reservation(self):
        identity = s.verify_session_token(self.token(), now=1200)
        self.assertEqual(identity, s.Session("user-1", "nonce-revocable-12345"))
        self.assertEqual(s.reserve_request(identity, now=1200), "accepted")

    def test_missing_settings_denied(self):
        with patch.dict(os.environ, {"SHAI_SESSION_PUBLIC_KEY_HEX":""}):
            self.assertIsNone(s.verify_session_token(self.token(), now=1200))

    def test_tampered_claim_denied(self):
        pieces = self.token().split(".")
        claims = json.loads(s._decode(pieces[1]))
        claims["sub"] = "attacker"
        pieces[1] = b64(json.dumps(claims).encode())
        self.assertIsNone(s.verify_session_token(".".join(pieces), now=1200))

    def test_bad_signature_and_alg_denied(self):
        self.assertIsNone(s.verify_session_token(self.token()[:-2] + "xx", now=1200))
        pieces = self.token().split(".")
        pieces[0] = b64(b'{"alg":"none","typ":"JWT"}')
        self.assertIsNone(s.verify_session_token(".".join(pieces), now=1200))

    def test_expired_and_wrong_audience(self):
        self.assertIsNone(s.verify_session_token(self.token(), now=2000))
        self.assertIsNone(s.verify_session_token(self.token(aud="wrong"), now=1200))

    def test_long_lived_and_bad_subject(self):
        self.assertIsNone(s.verify_session_token(self.token(exp=2001), now=1200))
        self.assertIsNone(s.verify_session_token(self.token(sub="../../x"), now=1200))

    def test_revocation_fails_closed(self):
        identity = s.verify_session_token(self.token(), now=1200)
        s.revoke_session(self.path, identity.jti)
        self.assertEqual(s.reserve_request(identity, now=1200), "revoked")

    def test_missing_db_fails_closed(self):
        identity = s.verify_session_token(self.token(), now=1200)
        os.unlink(self.path)
        self.assertEqual(s.reserve_request(identity, now=1200), "unavailable")

    def test_user_quota_enforced(self):
        identity = s.verify_session_token(self.token(), now=1200)
        for i in range(s.MAX_USER_REQUESTS):
            self.assertEqual(s.reserve_request(identity, now=1200 + 61*i), "accepted")
        self.assertEqual(s.reserve_request(identity, now=9000), "limited")

    def test_cross_process_limit_survives_new_calls(self):
        identity = s.verify_session_token(self.token(), now=1200)
        for i in range(s.MAX_USER_MINUTE):
            self.assertEqual(s.reserve_request(identity, now=1200), "accepted")
        self.assertEqual(s.reserve_request(identity, now=1200), "limited")

    def test_reject_nan_clock(self):
        identity = s.verify_session_token(self.token(), now=1200)
        self.assertEqual(s.reserve_request(identity, now=float("nan")), "unavailable")


if __name__ == "__main__":
    unittest.main()
