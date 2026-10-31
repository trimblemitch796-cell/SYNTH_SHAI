"""Adversarial offline tests for authenticated operator revocation."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from offline_approval_v1 import HOLD, SIGNED_FIELDS, canonical, revoke_operator, validate_once
from offline_operator_admin_v2 import DOMAIN, REVOKED, SIGNED, authenticated_revoke


class AdminV2Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = str(Path(temp.name) / "approval.sqlite")
        self.now = 1000000
        self.admin = Ed25519PrivateKey.generate()
        pub = self.admin.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        self.admin_keys = {"admin-test": pub}
        self.user = Ed25519PrivateKey.generate()
        self.user_keys = {"operator-test": self.user.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)}
        self.request = {"request_id": "demo-1", "action": "simulation",
                        "plan_sha256": hashlib.sha256(b"plan").hexdigest()}

    def signed_revoke(self, **changes):
        data = {"operation": "revoke_operator", "admin_id": "admin-test",
                "operator_id": "operator-test", "nonce": "admin-nonce-00000001",
                "expires_at": self.now + 60}
        data.update(changes)
        data["signature"] = self.admin.sign(DOMAIN + canonical({k: data[k] for k in SIGNED})).hex()
        return data

    def signed_approval(self):
        data = {**self.request, "operator_id": "operator-test",
                "nonce": "operator-nonce-00001", "expires_at": self.now + 60}
        data["signature"] = self.user.sign(canonical({k: data[k] for k in SIGNED_FIELDS})).hex()
        return data

    def revoke(self, data=None, **kw):
        return authenticated_revoke(self.signed_revoke() if data is None else data,
            pinned_admin_keys=kw.get("keys", self.admin_keys),
            trusted_database_path=kw.get("db", self.db),
            now=kw.get("now", self.now))

    def test_signed_admin_can_revoke(self):
        self.assertEqual(self.revoke(), REVOKED)
        self.assertEqual(validate_once(self.request, self.signed_approval(),
            trusted_operator_keys=self.user_keys,
            trusted_database_path=self.db, now=self.now), HOLD)

    def test_legacy_unauthenticated_revocation_denied(self):
        self.assertFalse(revoke_operator("operator-test", trusted_database_path=self.db))
        self.assertEqual(self.revoke(), REVOKED)

    def test_forgery_holds(self):
        d = self.signed_revoke()
        self.assertEqual(self.revoke({**d, "signature": "00" * 64}), HOLD)

    def test_replay_holds(self):
        d = self.signed_revoke()
        self.assertEqual(self.revoke(d), REVOKED)
        self.assertEqual(self.revoke(d), HOLD)

    def test_expired_holds(self):
        self.assertEqual(self.revoke(now=self.now + 61), HOLD)

    def test_tampered_target_holds(self):
        self.assertEqual(self.revoke({**self.signed_revoke(), "operator_id": "other"}), HOLD)

    def test_untrusted_admin_holds(self):
        self.assertEqual(self.revoke(keys={}), HOLD)

    def test_malformed_schema_holds(self):
        self.assertEqual(self.revoke({**self.signed_revoke(), "force": True}), HOLD)
        self.assertEqual(self.revoke({}), HOLD)

    def test_bad_clock_and_store_hold(self):
        self.assertEqual(self.revoke(now=float("nan")), HOLD)
        self.assertEqual(self.revoke(db=":memory:"), HOLD)

    def test_bad_signature_does_not_consume_nonce(self):
        d = self.signed_revoke()
        self.assertEqual(self.revoke({**d, "signature": "00" * 64}), HOLD)
        self.assertEqual(self.revoke(d), REVOKED)

    def test_wrong_operation_holds(self):
        self.assertEqual(self.revoke({**self.signed_revoke(), "operation": "grant"}), HOLD)

    def test_admin_cannot_be_self_declared(self):
        d = self.signed_revoke(admin_id="unknown")
        self.assertEqual(self.revoke(d), HOLD)


if __name__ == "__main__":
    unittest.main()
