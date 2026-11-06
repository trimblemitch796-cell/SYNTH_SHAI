"""Offline Android/OIDC handoff negative cases.

No Android app, identity provider, PKCE exchange, signing service, network
request, or SHAI action is created. These cases prove only that an *unissued*
or attacker-issued token is not accepted by the existing gateway verifier.
"""
import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from SYNTH_SHAI_staging_gateway import pilot_security as security


def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class AndroidIdentityBoundaryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = str(Path(directory.name) / "gate.sqlite")
        security.initialize_store(self.database)
        self.issuer_key = Ed25519PrivateKey.generate()
        public = self.issuer_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        env = patch.dict(os.environ, {
            "SHAI_SESSION_ISSUER": "https://identity.example.invalid",
            "SHAI_SESSION_AUDIENCE": "shai-staging",
            "SHAI_SESSION_PUBLIC_KEY_HEX": public.hex(),
            "SHAI_GATEWAY_DB": self.database,
        })
        env.start()
        self.addCleanup(env.stop)
        self.now = 1200

    def encode(self, *, key=None, claims=None, header=None):
        claims = dict({
            "iss": "https://identity.example.invalid",
            "aud": "shai-staging",
            "sub": "owner-1",
            "jti": "unique-session-001",
            "iat": 1000,
            "nbf": 1000,
            "exp": 1900,
        } if claims is None else claims)
        header = {"alg": "EdDSA", "typ": "JWT"} if header is None else header
        a = _b64(json.dumps(header, separators=(",", ":")).encode())
        b = _b64(json.dumps(claims, separators=(",", ":")).encode())
        signature = (key or self.issuer_key).sign((a + "." + b).encode("ascii"))
        return a + "." + b + "." + _b64(signature)

    def test_only_trusted_signed_session_is_accepted(self):
        identity = security.verify_session_token(self.encode(), now=self.now)
        self.assertEqual(identity, security.Session("owner-1", "unique-session-001"))

    def test_android_client_cannot_self_sign_its_session(self):
        attacker_key = Ed25519PrivateKey.generate()
        self.assertIsNone(security.verify_session_token(
            self.encode(key=attacker_key), now=self.now
        ))

    def test_untrusted_key_claim_in_jwt_header_is_not_accepted(self):
        attacker_key = Ed25519PrivateKey.generate()
        forged = self.encode(
            key=attacker_key,
            header={"alg": "EdDSA", "typ": "JWT", "jwk": {"kty": "OKP"}},
        )
        self.assertIsNone(security.verify_session_token(forged, now=self.now))

    def test_oauth_authorization_code_is_not_a_gateway_session(self):
        for value in ("code-from-redirect", "444000", "id-token-from-another-provider"):
            with self.subTest(value=value):
                self.assertIsNone(security.verify_session_token(value, now=self.now))

    def test_other_provider_id_token_claims_are_not_automatically_accepted(self):
        claims = {
            "iss": "https://identity.example.invalid",
            "aud": "shai-staging",
            "sub": "owner-1",
            "iat": 1000,
            "nbf": 1000,
            "exp": 1900,
            "email": "untrusted-claim@example.invalid",
        }
        self.assertIsNone(security.verify_session_token(
            self.encode(claims=claims), now=self.now
        ))

    def test_session_does_not_survive_expiry_or_exceed_fifteen_minutes(self):
        self.assertIsNone(security.verify_session_token(self.encode(), now=1900))
        claims = {
            "iss": "https://identity.example.invalid",
            "aud": "shai-staging",
            "sub": "owner-1",
            "jti": "long-lived-session-002",
            "iat": 1000,
            "nbf": 1000,
            "exp": 1901,
        }
        self.assertIsNone(security.verify_session_token(
            self.encode(claims=claims), now=self.now
        ))

    def test_missing_trusted_public_key_cannot_enable_mobile_signin(self):
        with patch.dict(os.environ, {"SHAI_SESSION_PUBLIC_KEY_HEX": ""}):
            self.assertIsNone(security.verify_session_token(self.encode(), now=self.now))

    def test_signed_session_remains_subject_to_revocation(self):
        identity = security.verify_session_token(self.encode(), now=self.now)
        self.assertEqual(security.reserve_request(identity, now=self.now), "accepted")
        security.revoke_session(self.database, identity.jti)
        self.assertEqual(security.reserve_request(identity, now=self.now), "revoked")


if __name__ == "__main__":
    unittest.main()
