"""Mock-only Google JWKS rotation tests: no real Google/Render/API calls."""
import base64
import json
import unittest
from unittest.mock import Mock

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from SYNTH_SHAI_staging_gateway.google_jwks_rotation import (
    GOOGLE_JWKS_URI, GoogleJwksCache, JwksRejected, MAX_JWKS_BYTES,
    fetch_pinned_google_jwks, parse_google_jwks, verify_with_cached_google_keys,
)

CLIENT = "1234567890-test.apps.googleusercontent.com"
NONCE = "a" * 43


def b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def jwk(key, kid):
    n = key.public_key().public_numbers().n
    return {"kty": "RSA", "alg": "RS256", "use": "sig", "kid": kid,
            "e": "AQAB", "n": b64(n.to_bytes(256, "big"))}


def jwt(key, kid):
    header = b64(json.dumps({"alg": "RS256", "kid": kid}, separators=(",", ":")).encode())
    claims = b64(json.dumps({
        "iss": "https://accounts.google.com", "aud": CLIENT,
        "nonce": NONCE, "sub": "109876543210123456789",
        "iat": 1000, "exp": 4000}, separators=(",", ":")).encode())
    data = (header + "." + claims).encode()
    return data.decode() + "." + b64(key.sign(data, padding.PKCS1v15(), hashes.SHA256()))


def payload(*keys):
    return json.dumps({"keys": list(keys)}, separators=(",", ":")).encode()


class GoogleJwksRotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.b = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.cache = GoogleJwksCache()
        self.a_response = payload(jwk(self.a, "google-A"))
        self.b_response = payload(jwk(self.b, "google-B"))

    def install(self, body=None, max_age="public, max-age=120", now=1):
        return self.cache.install_trusted_response(
            self.a_response if body is None else body,
            max_age, GOOGLE_JWKS_URI, now=now)

    def test_rotation_replaces_not_accumulates_old_keys(self):
        self.assertEqual(self.install(), 1)
        self.assertEqual(set(self.cache.snapshot(now=2)), {"google-A"})
        self.install(self.b_response, now=3)
        self.assertEqual(set(self.cache.snapshot(now=4)), {"google-B"})

    def test_valid_signed_token_verified_only_under_fresh_matching_key(self):
        self.install()
        token_a = jwt(self.a, "google-A")
        self.assertIsNotNone(verify_with_cached_google_keys(
            token_a, self.cache, client_id=CLIENT, expected_nonce=NONCE,
            now=2000, cache_now=20))
        self.install(self.b_response, now=21)
        self.assertIsNone(verify_with_cached_google_keys(
            token_a, self.cache, client_id=CLIENT, expected_nonce=NONCE,
            now=2000, cache_now=22))
        self.assertIsNotNone(verify_with_cached_google_keys(
            jwt(self.b, "google-B"), self.cache,
            client_id=CLIENT, expected_nonce=NONCE, now=2000, cache_now=22))

    def test_unknown_kid_no_client_triggered_fetch(self):
        self.install()
        self.assertIsNone(verify_with_cached_google_keys(
            jwt(self.b, "google-B"), self.cache, client_id=CLIENT,
            expected_nonce=NONCE, now=2000, cache_now=2))

    def test_stale_cache_never_silently_reuses_keys(self):
        self.install(max_age="max-age=3", now=100)
        self.assertTrue(self.cache.snapshot(now=102))
        self.assertEqual(self.cache.snapshot(now=103), {})
        self.assertIsNone(verify_with_cached_google_keys(
            jwt(self.a, "google-A"), self.cache, client_id=CLIENT,
            expected_nonce=NONCE, now=2000, cache_now=103))

    def test_bad_refresh_never_extends_cache_expiry(self):
        self.install(max_age="max-age=10", now=10)
        with self.assertRaises(JwksRejected):
            self.install(payload(jwk(self.a, "google-A"), jwk(self.b, "google-A")),
                         now=11)
        self.assertTrue(self.cache.snapshot(now=19))
        self.assertEqual(self.cache.snapshot(now=20), {})

    def test_pinned_uri_and_disallow_redirect_content(self):
        with self.assertRaises(JwksRejected):
            self.cache.install_trusted_response(
                self.a_response, "max-age=50", "https://evil.invalid/jwks", now=1)

    def test_reject_duplicate_kid_and_unexpected_alg_kty_use(self):
        for item in (
            payload(jwk(self.a, "dup"), jwk(self.b, "dup")),
            payload(dict(jwk(self.a, "a"), alg="HS256")),
            payload(dict(jwk(self.a, "a"), kty="EC")),
            payload(dict(jwk(self.a, "a"), use="enc")),
            payload(dict(jwk(self.a, "a"), jku="https://evil.invalid")),
        ):
            with self.subTest(item=item[:45]):
                with self.assertRaises(JwksRejected):
                    parse_google_jwks(item)

    def test_reject_malformed_oversized_duplicate_json_and_noncanonical_modulus(self):
        bad = [
            b"", b"<html>error</html>", b"x" * (MAX_JWKS_BYTES + 1),
            b'{"keys":[]}',
            b'{"keys":[],"keys":[]}',
            payload(dict(jwk(self.a, "a"), n="AAAA=")),
            payload(dict(jwk(self.a, "a"), e="AQAB=")),
        ]
        for blob in bad:
            with self.subTest(blob=blob[:40]):
                with self.assertRaises(JwksRejected):
                    parse_google_jwks(blob)

    def test_no_cache_or_invalid_max_age_fails_closed(self):
        for value in ("", "private, max-age=600", "no-cache, max-age=600",
                      "max-age=0", "max-age=-1", "max-age=x",
                      "max-age=12,max-age=13"):
            with self.subTest(value=value):
                with self.assertRaises(JwksRejected):
                    self.install(max_age=value)

    def test_limits_max_age_to_one_day(self):
        self.install(max_age="public, max-age=999999", now=3)
        self.assertTrue(self.cache.snapshot(now=3+86400-1))
        self.assertEqual(self.cache.snapshot(now=3+86400), {})

    def test_invalid_time_is_rejected(self):
        with self.assertRaises(JwksRejected):
            self.install(now=float("nan"))
        self.install(now=3)
        with self.assertRaises(JwksRejected):
            self.cache.snapshot(now=-1)

    def test_network_fetcher_is_explicit_and_rejects_wrong_host(self):
        response = Mock()
        response.geturl.return_value = "https://attacker.invalid/jwks"
        response.status = 200
        response.headers = {"Content-Type": "application/json",
                            "Cache-Control": "max-age=30"}
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        http = Mock()
        http.open.return_value = response
        with self.assertRaises(JwksRejected):
            fetch_pinned_google_jwks(opener=http)
        self.assertEqual(http.open.call_args[0][0].full_url, GOOGLE_JWKS_URI)

    def test_trusted_https_response_can_rotate_after_expiry_in_mock(self):
        class FakeResponse:
            status = 200
            headers = {"Content-Type": "application/json", "Cache-Control": "max-age=10"}
            def __init__(self, body):
                self.body = body
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return GOOGLE_JWKS_URI
            def read(self, length): return self.body[:length]
        class FakeOpener:
            def __init__(self, body): self.body = body
            def open(self, req, timeout): return FakeResponse(self.body)
        self.cache.refresh(opener=FakeOpener(self.a_response), now=3)
        self.assertEqual(set(self.cache.snapshot(now=4)), {"google-A"})
        self.cache.refresh(opener=FakeOpener(self.b_response), now=14)
        self.assertEqual(set(self.cache.snapshot(now=15)), {"google-B"})


if __name__ == "__main__":
    unittest.main()
