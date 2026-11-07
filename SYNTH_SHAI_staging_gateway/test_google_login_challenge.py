"""Offline one-use Google login challenge tests. No live Google/Render/OpenAI."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from SYNTH_SHAI_staging_gateway.google_login_challenge import (
    CHALLENGE_TTL_SECONDS, initialize_challenge_store, issue_challenge,
    consume_challenge, verify_and_consume_google_preflight,
)
from SYNTH_SHAI_staging_gateway.google_oidc_preflight import VerifiedGoogleSubject

BINDING = hashlib.sha256(b"server-issued-session-fixture").hexdigest()
OTHER_BINDING = hashlib.sha256(b"other-session").hexdigest()
CLIENT = "1234567890-test.apps.googleusercontent.com"


def b64(data):
    if type(data) is not bytes:
        data = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


class GoogleLoginChallengeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = str(Path(tmp.name) / "challenge.sqlite")
        initialize_challenge_store(self.path)
        self.now = 2000

    def issue(self, *, binding=BINDING):
        out = issue_challenge(self.path, binding, now=self.now)
        self.assertIsNotNone(out)
        return out

    def test_issue_entropy_expiry_and_distinct_transactions(self):
        a = self.issue()
        b = self.issue()
        self.assertEqual(len(a.transaction_id), 43)
        self.assertEqual(len(a.nonce), 43)
        self.assertNotEqual(a.nonce, b.nonce)
        self.assertNotEqual(a.transaction_id, b.transaction_id)
        self.assertNotEqual(a.nonce, a.transaction_id)
        self.assertEqual(a.expires_at, self.now + 300)

    def test_first_valid_consume_then_replay_denied(self):
        a = self.issue()
        self.assertTrue(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))

    def test_wrong_nonce_burns_only_target_transaction(self):
        a, b = self.issue(), self.issue()
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, b.nonce, BINDING, now=self.now))
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))
        self.assertTrue(consume_challenge(
            self.path, b.transaction_id, b.nonce, BINDING, now=self.now))

    def test_wrong_binding_burns_transaction_and_rebind_denied(self):
        a = self.issue()
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, OTHER_BINDING, now=self.now))
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))

    def test_expiry_boundary_fails_and_consumes(self):
        a = self.issue()
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING,
            now=self.now + CHALLENGE_TTL_SECONDS))
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))

    def test_clock_rollback_rejected_then_still_one_use(self):
        a = self.issue()
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now - 1))
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))

    def test_missing_or_uninitialized_db_fails_closed(self):
        missing = self.path + ".missing"
        self.assertIsNone(issue_challenge(missing, BINDING, now=self.now))
        a = self.issue()
        self.assertFalse(consume_challenge(
            missing, a.transaction_id, a.nonce, BINDING, now=self.now))
        self.assertTrue(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))
        empty_db = str(Path(self.path).parent / "uninitialized.sqlite")
        Path(empty_db).touch()
        self.assertIsNone(issue_challenge(empty_db, BINDING, now=self.now))

    def test_invalid_transaction_and_binding_are_denied(self):
        a = self.issue()
        self.assertFalse(consume_challenge(
            self.path, "guessable-id", a.nonce, BINDING, now=self.now))
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, "client-controlled", now=self.now))
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))
        self.assertIsNone(issue_challenge(self.path, "bad-binding", now=self.now))

    def test_two_parallel_consumers_only_one_can_succeed(self):
        a = self.issue()
        def consume(_):
            return consume_challenge(
                self.path, a.transaction_id, a.nonce, BINDING, now=self.now)
        with ThreadPoolExecutor(max_workers=2) as pool:
            successes = list(pool.map(consume, range(2)))
        self.assertEqual(sum(successes), 1)

    def test_invalid_clock_fails_closed_and_does_not_create_challenge(self):
        self.assertIsNone(issue_challenge(self.path, BINDING, now=float("nan")))
        self.assertIsNone(issue_challenge(self.path, BINDING, now=True))
        a = self.issue()
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=float("inf")))
        self.assertTrue(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))

    def test_token_verification_is_one_use_and_returns_only_google_sub(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        a = self.issue()
        header = {"alg": "RS256", "kid": "synthetic-kid", "typ": "JWT"}
        claims = {
            "iss": "https://accounts.google.com",
            "aud": CLIENT, "sub": "109876543210123456789",
            "nonce": a.nonce, "iat": 1000, "exp": 4600,
        }
        signed = b64(header) + "." + b64(claims)
        signature = b64(key.sign(signed.encode("ascii"),
                                 padding.PKCS1v15(), hashes.SHA256()))
        token = signed + "." + signature
        options = dict(path=self.path, transaction_id=a.transaction_id,
                       nonce=a.nonce, trusted_binding_hash=BINDING,
                       client_id=CLIENT,
                       trusted_public_keys={"synthetic-kid": key.public_key()},
                       now=self.now)
        self.assertEqual(
            verify_and_consume_google_preflight(token, **options),
            VerifiedGoogleSubject("109876543210123456789"))
        self.assertIsNone(verify_and_consume_google_preflight(token, **options))

    def test_bad_token_consumes_challenge_before_any_retry(self):
        a = self.issue()
        options = dict(path=self.path, transaction_id=a.transaction_id,
                       nonce=a.nonce, trusted_binding_hash=BINDING,
                       client_id=CLIENT, trusted_public_keys={}, now=self.now)
        self.assertIsNone(verify_and_consume_google_preflight("forged", **options))
        self.assertFalse(consume_challenge(
            self.path, a.transaction_id, a.nonce, BINDING, now=self.now))


if __name__ == "__main__":
    unittest.main()
