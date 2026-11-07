"""Offline stateful pre-auth cookie/session ownership and replay tests."""
from concurrent.futures import ThreadPoolExecutor
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from SYNTH_SHAI_staging_gateway.google_server_binding import (
    COOKIE_NAME, CLEAR_COOKIE, initialize_preauth_store,
    issue_preauth_cookie, start_bound_google_login, finish_bound_google_login,
    revoke_preauth_cookie,
)
from SYNTH_SHAI_staging_gateway.google_oidc_preflight import VerifiedGoogleSubject

ORIGIN = "https://login.example.invalid"
CLIENT = "1234567890-test.apps.googleusercontent.com"


def b64(value):
    if type(value) is not bytes:
        value = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


class GoogleServerBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = str(Path(self.dir.name) / "session.sqlite")
        initialize_preauth_store(self.path)
        self.now = 2000

    def cookie(self):
        c = issue_preauth_cookie(self.path, now=self.now)
        self.assertIsNotNone(c)
        return c

    def header(self, c):
        return COOKIE_NAME + "=" + c.cookie_value

    def start(self, c, **overrides):
        values = dict(request_origin=ORIGIN, configured_origin=ORIGIN, now=self.now)
        values.update(overrides)
        return start_bound_google_login(self.path, self.header(c), **values)

    def token(self, nonce):
        header = b64({"alg": "RS256", "kid": "synthetic", "typ": "JWT"})
        claims = b64({"iss": "https://accounts.google.com", "aud": CLIENT,
                      "sub": "109876543210123456789", "nonce": nonce,
                      "iat": 1000, "exp": 4600})
        msg = (header + "." + claims).encode("ascii")
        sig = self.key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
        return msg.decode() + "." + b64(sig)

    def finish(self, c, challenge, token=None, **overrides):
        values = dict(request_origin=ORIGIN, configured_origin=ORIGIN,
                      transaction_id=challenge.transaction_id, nonce=challenge.nonce,
                      raw_google_token=self.token(challenge.nonce) if token is None else token,
                      client_id=CLIENT,
                      trusted_public_keys={"synthetic": self.key.public_key()},
                      now=self.now)
        values.update(overrides)
        return finish_bound_google_login(self.path, self.header(c), **values)

    def test_server_cookie_secure_host_only_and_redacted_repr(self):
        c = self.cookie()
        self.assertEqual(len(c.cookie_value), 43)
        self.assertIn("__Host-", c.set_cookie)
        self.assertIn("Secure", c.set_cookie)
        self.assertIn("HttpOnly", c.set_cookie)
        self.assertIn("SameSite=Strict", c.set_cookie)
        self.assertIn("Path=/", c.set_cookie)
        self.assertNotIn("Domain=", c.set_cookie)
        self.assertNotIn(c.cookie_value, repr(c))
        self.assertIn("Max-Age=0", CLEAR_COOKIE)

    def test_one_cookie_allows_only_one_challenge(self):
        c = self.cookie()
        a = self.start(c)
        self.assertIsNotNone(a)
        self.assertIsNone(self.start(c))

    def test_verified_cookie_bound_token_completes_only_once(self):
        c = self.cookie()
        tx = self.start(c)
        self.assertEqual(self.finish(c, tx), VerifiedGoogleSubject("109876543210123456789"))
        self.assertIsNone(self.finish(c, tx))
        self.assertIsNone(self.start(c))

    def test_wrong_session_cannot_claim_another_challenge(self):
        a, b = self.cookie(), self.cookie()
        tx = self.start(a)
        self.assertIsNone(self.finish(b, tx))
        self.assertEqual(self.finish(a, tx), VerifiedGoogleSubject("109876543210123456789"))

    def test_forged_cookie_is_not_auto_registered(self):
        c = self.cookie()
        tx = self.start(c)
        spoof = COOKIE_NAME + "=" + "X" * 43
        self.assertIsNone(start_bound_google_login(
            self.path, spoof, request_origin=ORIGIN, configured_origin=ORIGIN, now=self.now))
        self.assertIsNone(finish_bound_google_login(
            self.path, spoof, request_origin=ORIGIN, configured_origin=ORIGIN,
            transaction_id=tx.transaction_id, nonce=tx.nonce,
            raw_google_token=self.token(tx.nonce), client_id=CLIENT,
            trusted_public_keys={"synthetic": self.key.public_key()}, now=self.now))
        self.assertEqual(self.finish(c, tx), VerifiedGoogleSubject("109876543210123456789"))

    def test_duplicate_cookie_fails_and_cannot_fixate_session(self):
        c = self.cookie()
        header = self.header(c) + "; " + self.header(c)
        self.assertIsNone(start_bound_google_login(
            self.path, header, request_origin=ORIGIN, configured_origin=ORIGIN, now=self.now))
        self.assertIsNotNone(self.start(c))

    def test_wrong_origin_and_untrusted_configured_origin_rejected(self):
        c = self.cookie()
        self.assertIsNone(self.start(c, request_origin="https://evil.example.invalid"))
        self.assertIsNone(self.start(c, configured_origin="http://login.example.invalid",
                                     request_origin="http://login.example.invalid"))
        self.assertIsNone(self.start(c, configured_origin="https://login.example.invalid/path",
                                     request_origin="https://login.example.invalid/path"))
        self.assertIsNotNone(self.start(c))

    def test_session_expiration_and_clock_rollback(self):
        c = self.cookie()
        self.assertIsNone(self.start(c, now=self.now - 1))
        self.assertIsNone(self.start(c, now=self.now + 300))

    def test_invalid_token_consumes_server_cookie(self):
        c = self.cookie()
        tx = self.start(c)
        self.assertIsNone(self.finish(c, tx, token="forged"))
        self.assertIsNone(self.finish(c, tx))

    def test_bad_nonce_attempt_consumes_server_cookie(self):
        c = self.cookie()
        tx = self.start(c)
        self.assertIsNone(self.finish(c, tx, nonce="attacker"))
        self.assertIsNone(self.finish(c, tx))

    def test_logout_rejects_later_callback(self):
        c = self.cookie()
        tx = self.start(c)
        self.assertTrue(revoke_preauth_cookie(self.path, self.header(c)))
        self.assertIsNone(self.finish(c, tx))

    def test_missing_db_and_invalid_clock_fail_closed(self):
        missing = self.path + ".missing"
        self.assertIsNone(issue_preauth_cookie(missing, now=self.now))
        self.assertIsNone(issue_preauth_cookie(self.path, now=float("nan")))
        self.assertIsNone(issue_preauth_cookie(self.path, now=True))

    def test_parallel_starts_can_create_only_one_challenge(self):
        c = self.cookie()
        with ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(lambda _: self.start(c), range(2)))
        self.assertEqual(sum(x is not None for x in values), 1)

    def test_parallel_callbacks_cannot_both_authenticate(self):
        c = self.cookie()
        tx = self.start(c)
        with ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(lambda _: self.finish(c, tx), range(2)))
        self.assertEqual(sum(x is not None for x in values), 1)

    def test_server_state_persists_across_callers_using_same_sqlite(self):
        c = self.cookie()
        tx = self.start(c)
        self.assertEqual(self.finish(c, tx), VerifiedGoogleSubject("109876543210123456789"))
        self.assertIsNone(self.finish(c, tx))

    def test_cookie_not_accepted_in_url_query_or_authorization_header(self):
        c = self.cookie()
        self.assertIsNone(start_bound_google_login(
            self.path, "?" + self.header(c), request_origin=ORIGIN,
            configured_origin=ORIGIN, now=self.now))
        self.assertIsNone(start_bound_google_login(
            self.path, "Bearer " + c.cookie_value, request_origin=ORIGIN,
            configured_origin=ORIGIN, now=self.now))


if __name__ == "__main__":
    unittest.main()
