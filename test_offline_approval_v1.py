"""Synthetic, offline-only tests for signed approval validation."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from offline_approval_v1 import HOLD, VALIDATED, SIGNED_FIELDS, canonical, revoke_operator, validate_once


class OfflineApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / "approval.sqlite")
        self.key = Ed25519PrivateKey.generate()
        public = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        self.keys = {"human-demo": public}
        self.request = {"request_id": "request-001", "action": "synthetic_review",
                        "plan_sha256": hashlib.sha256(b"synthetic plan").hexdigest()}
        self.now = 1000000
        self.approval = self.make_approval()

    def make_approval(self, **changes):
        data = {**self.request, "operator_id": "human-demo",
                "nonce": "single-use-challenge-00001", "expires_at": self.now + 60}
        data.update(changes)
        data["signature"] = self.key.sign(
            canonical({k: data[k] for k in SIGNED_FIELDS})).hex()
        return data

    def check(self, request=None, approval=None, **kwargs):
        return validate_once(
            self.request if request is None else request,
            self.approval if approval is None else approval,
            trusted_operator_keys=kwargs.get("keys", self.keys),
            trusted_database_path=kwargs.get("db", self.db),
            now=kwargs.get("now", self.now))

    def test_valid_signature_never_executes(self):
        self.assertEqual(self.check(), VALIDATED)

    def test_replay_holds_even_after_reopen(self):
        self.assertEqual(self.check(), VALIDATED)
        self.assertEqual(self.check(), HOLD)

    def test_missing_approval_holds(self):
        self.assertEqual(self.check(approval={}), HOLD)

    def test_forged_signature_holds(self):
        forged = {**self.approval, "signature": "00" * 64}
        self.assertEqual(self.check(approval=forged), HOLD)

    def test_untrusted_operator_holds(self):
        self.assertEqual(self.check(keys={}), HOLD)

    def test_tampered_action_holds(self):
        changed = {**self.approval, "action": "different"}
        self.assertEqual(self.check(approval=changed), HOLD)

    def test_tampered_plan_holds(self):
        changed = {**self.approval, "plan_sha256": "0" * 64}
        self.assertEqual(self.check(approval=changed), HOLD)

    def test_expired_holds(self):
        self.assertEqual(self.check(now=self.now + 61), HOLD)

    def test_unreasonably_long_expiry_holds(self):
        self.assertEqual(self.check(approval=self.make_approval(expires_at=self.now + 10000)), HOLD)

    def test_legacy_unsigned_revocation_fails_closed(self):
        self.assertFalse(revoke_operator("human-demo", trusted_database_path=self.db))
        self.assertEqual(self.check(), VALIDATED)

    def test_bad_storage_holds(self):
        self.assertEqual(self.check(db=":memory:"), HOLD)

    def test_no_extra_fields_or_truthy_clock(self):
        self.assertEqual(self.check(approval={**self.approval, "approved": True}), HOLD)
        self.assertEqual(self.check(now=True), HOLD)

    def test_invalid_attempt_does_not_consume_nonce(self):
        bad = {**self.approval, "signature": "00" * 64}
        self.assertEqual(self.check(approval=bad), HOLD)
        self.assertEqual(self.check(), VALIDATED)


if __name__ == "__main__":
    unittest.main()
