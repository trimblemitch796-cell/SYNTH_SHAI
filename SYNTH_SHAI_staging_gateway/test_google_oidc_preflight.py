"""Synthetic offline Google ID-token negative-path checks. No Google/network/API."""
import base64
import json
import unittest

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from SYNTH_SHAI_staging_gateway.google_oidc_preflight import (
    VerifiedGoogleSubject, verify_google_id_token,
)
from SYNTH_SHAI_staging_gateway.pilot_security import verify_session_token

CLIENT = "1234567890-test.apps.googleusercontent.com"
OTHER_CLIENT = "9876543210-attacker.apps.googleusercontent.com"
ANDROID_PARTY = "2222222222-android.apps.googleusercontent.com"
NONCE = "a" * 43
KID = "synthetic-rotation-key"


def _b64(value):
    if type(value) is not bytes:
        value = json.dumps(value, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


class GoogleOidcPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.claims = {
            "iss": "https://accounts.google.com",
            "aud": CLIENT,
            "sub": "109876543210123456789",
            "nonce": NONCE,
            "iat": 1000,
            "exp": 4600,
        }
        self.keys = {KID: self.key.public_key()}

    def signed(self, claims=None, *, header=None, key=None, raw_claims=None):
        header = {"alg": "RS256", "kid": KID, "typ": "JWT"} if header is None else header
        a = _b64(header)
        b = _b64(self.claims if claims is None else claims) if raw_claims is None else _b64(raw_claims)
        signing_input = a + "." + b
        private = self.key if key is None else key
        sig = private.sign(signing_input.encode("ascii"),
                           padding.PKCS1v15(), hashes.SHA256())
        return signing_input + "." + _b64(sig)

    def verify(self, token, **overrides):
        options = dict(client_id=CLIENT, expected_nonce=NONCE,
                       trusted_public_keys=self.keys, now=2000)
        options.update(overrides)
        return verify_google_id_token(token, **options)

    def test_verified_signed_fixture_returns_only_opaque_google_sub(self):
        self.claims.update({"email": "a@sample.invalid",
                            "name": "Unverified claimed name", "is_admin": True})
        self.assertEqual(self.verify(self.signed()),
                         VerifiedGoogleSubject("109876543210123456789"))
        self.assertFalse(hasattr(self.verify(self.signed()), "email"))

    def test_both_google_issuer_variants(self):
        for issuer in ("accounts.google.com", "https://accounts.google.com"):
            with self.subTest(issuer=issuer):
                self.claims["iss"] = issuer
                self.assertIsNotNone(self.verify(self.signed()))

    def test_wrong_issuer_audience_or_array_audience(self):
        for field, bad in (("iss", "https://attacker.example.invalid"),
                           ("aud", OTHER_CLIENT), ("aud", [CLIENT])):
            with self.subTest(field=field, bad=bad):
                original = self.claims[field]
                self.claims[field] = bad
                self.assertIsNone(self.verify(self.signed()))
                self.claims[field] = original

    def test_nonce_mismatch_missing_or_too_short_expected_nonce(self):
        self.assertIsNone(self.verify(self.signed(), expected_nonce="b" * 43))
        del self.claims["nonce"]
        self.assertIsNone(self.verify(self.signed()))
        self.claims["nonce"] = NONCE
        self.assertIsNone(self.verify(self.signed(), expected_nonce="test"))

    def test_expiry_future_issuance_and_excessive_lifetime(self):
        self.assertIsNone(self.verify(self.signed(), now=4600))
        self.assertIsNone(self.verify(self.signed(), now=999))
        self.claims["exp"] = 5000
        self.assertIsNone(self.verify(self.signed()))
        self.claims["exp"] = 1999
        self.assertIsNone(self.verify(self.signed()))

    def test_future_nbf_and_noninteger_dates(self):
        self.claims["nbf"] = 3000
        self.assertIsNone(self.verify(self.signed()))
        del self.claims["nbf"]
        for field, bad in (("iat", True), ("exp", 4600.5)):
            with self.subTest(field=field):
                self.claims[field] = bad
                self.assertIsNone(self.verify(self.signed()))
                self.claims[field] = 1000 if field == "iat" else 4600

    def test_signature_invalid_even_with_trusted_kid(self):
        self.assertIsNone(self.verify(self.signed(key=self.other_key)))

    def test_unknown_kid_and_untrusted_header_urls(self):
        self.assertIsNone(self.verify(self.signed(header={"alg": "RS256", "kid": "unknown"})))
        self.assertIsNone(self.verify(self.signed(header={
            "alg": "RS256", "kid": KID, "jku": "https://attacker.invalid/jwks"
        })))
        self.assertIsNone(self.verify(self.signed(header={
            "alg": "RS256", "kid": KID, "jwk": {"kty": "RSA"}
        })))

    def test_alg_none_hs256_and_unexpected_typ_fail_closed(self):
        for header in ({"alg": "none", "kid": KID},
                       {"alg": "HS256", "kid": KID},
                       {"alg": "RS256", "kid": KID, "typ": "AT+JWT"}):
            with self.subTest(header=header):
                self.assertIsNone(self.verify(self.signed(header=header)))

    def test_duplicate_claim_fields_fail_even_when_signed(self):
        claims = b'{"iss":"https://accounts.google.com","iss":"accounts.google.com","aud":"' + CLIENT.encode() + b'","sub":"109876543210123456789","nonce":"' + NONCE.encode() + b'","iat":1000,"exp":4600}'
        self.assertIsNone(self.verify(self.signed(raw_claims=claims)))

    def test_noncanonical_and_malformed_segments_fail(self):
        token = self.signed()
        self.assertIsNone(self.verify(token + "="))
        self.assertIsNone(self.verify(token + ".fourth"))
        self.assertIsNone(self.verify("444000"))
        self.assertIsNone(self.verify("x" * 8193))

    def test_authorised_party_requires_explicit_pin(self):
        self.claims["azp"] = ANDROID_PARTY
        self.assertIsNone(self.verify(self.signed()))
        self.assertEqual(self.verify(self.signed(), authorized_party=ANDROID_PARTY),
                         VerifiedGoogleSubject("109876543210123456789"))
        self.assertIsNone(self.verify(self.signed(), authorized_party=OTHER_CLIENT))

    def test_wrong_or_missing_public_keys_fails_closed(self):
        self.assertIsNone(self.verify(self.signed(), trusted_public_keys={}))
        self.assertIsNone(self.verify(self.signed(), trusted_public_keys={
            KID: self.other_key.public_key()
        }))
        self.assertIsNone(self.verify(self.signed(), trusted_public_keys={
            KID: "RSA_PUBLIC_KEY_TEXT_SUPPLIED_BY_CLIENT"
        }))

    def test_missing_bad_subject_and_unsigned_email_are_not_identity(self):
        self.claims["sub"] = "wrong/sub"
        self.assertIsNone(self.verify(self.signed()))
        self.claims["sub"] = False
        self.assertIsNone(self.verify(self.signed()))
        self.claims["sub"] = "109876543210123456789"
        self.claims["email"] = "owner@example.invalid"
        self.assertEqual(self.verify(self.signed()).subject, self.claims["sub"])

    def test_untrusted_client_id_or_clock_fails_closed(self):
        self.assertIsNone(self.verify(self.signed(), client_id=OTHER_CLIENT))
        self.assertIsNone(self.verify(self.signed(), client_id=""))
        self.assertIsNone(self.verify(self.signed(), now=float("nan")))
        self.assertIsNone(self.verify(self.signed(), now=True))

    def test_google_id_token_is_not_a_shai_session(self):
        self.assertIsNone(verify_session_token(self.signed(), now=2000))

    def test_malformed_json_nan_and_duplicate_header_fail(self):
        raw = b'{"iss":"https://accounts.google.com","aud":"' + CLIENT.encode() + b'","sub":"109876543210123456789","nonce":"' + NONCE.encode() + b'","iat":NaN,"exp":4600}'
        self.assertIsNone(self.verify(self.signed(raw_claims=raw)))
        token = self.signed(header={"alg": "RS256", "kid": KID})
        a, b, c = token.split(".")
        dupheader = _b64(b'{"alg":"RS256","alg":"RS256","kid":"' + KID.encode() + b'"}')
        signature = self.key.sign((dupheader + "." + b).encode("ascii"), padding.PKCS1v15(), hashes.SHA256())
        self.assertIsNone(self.verify(dupheader + "." + b + "." + _b64(signature)))


if __name__ == "__main__":
    unittest.main()
