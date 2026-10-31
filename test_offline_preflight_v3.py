"""Default-deny preflight regression tests: no execution authority."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from offline_approval_v1 import HOLD, SIGNED_FIELDS, canonical
from offline_preflight_v3 import PROHIBITED, REVIEW, PreflightPolicy, evaluate_preflight


class OfflinePreflightTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = str(Path(tmp.name) / "preflight.sqlite")
        self.key = Ed25519PrivateKey.generate()
        raw = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        self.keys = {"human": raw}
        self.now = 100000
        self.request = {"request_id": "req-1", "action": "synthetic_review",
                        "plan_sha256": hashlib.sha256(b"synthetic").hexdigest()}
        self.policy = PreflightPolicy(frozenset({"synthetic_review"}))
        self.approval = self.sign()

    def sign(self, **overrides):
        payload = dict(self.request, operator_id="human",
                       nonce="unique-nonce-0000000001", expires_at=self.now + 60)
        payload.update(overrides)
        payload["signature"] = self.key.sign(
            canonical({field: payload[field] for field in SIGNED_FIELDS})).hex()
        return payload

    def decide(self, request=None, approval=None, policy=None, **changes):
        return evaluate_preflight(
            self.request if request is None else request,
            self.approval if approval is None else approval,
            policy=self.policy if policy is None else policy,
            trusted_operator_keys=changes.get("keys", self.keys),
            trusted_database_path=changes.get("db", self.db),
            now=changes.get("now", self.now))

    def test_valid_request_is_review_not_execution(self):
        self.assertEqual(self.decide(), REVIEW)

    def test_replay_holds(self):
        self.assertEqual(self.decide(), REVIEW)
        self.assertEqual(self.decide(), HOLD)

    def test_request_id_reuse_with_new_nonce_holds(self):
        self.assertEqual(self.decide(), REVIEW)
        self.assertEqual(self.decide(approval=self.sign(nonce="unique-nonce-0000000002")), HOLD)

    def test_default_deny_unknown_action(self):
        request = dict(self.request, action="unlisted")
        self.assertEqual(self.decide(request=request), HOLD)

    def test_prohibited_action_never_allowed_even_if_listed(self):
        request = dict(self.request, action="transfer_funds")
        policy = PreflightPolicy(frozenset({"transfer_funds"}))
        self.assertEqual(self.decide(request=request, policy=policy), HOLD)

    def test_policy_cannot_remove_mandatory_denies(self):
        policy = PreflightPolicy(frozenset({"synthetic_review"}), frozenset())
        self.assertEqual(self.decide(policy=policy), HOLD)

    def test_invalid_policy_does_not_consume_signature(self):
        self.assertEqual(self.decide(policy=PreflightPolicy(frozenset())), HOLD)
        self.assertEqual(self.decide(), REVIEW)

    def test_invalid_action_does_not_consume_nonce(self):
        request = dict(self.request, action="transfer_funds")
        self.assertEqual(self.decide(request=request), HOLD)
        self.assertEqual(self.decide(), REVIEW)

    def test_signature_forgery_holds(self):
        self.assertEqual(self.decide(approval={**self.approval, "signature": "00"*64}), HOLD)

    def test_untrusted_operator_holds(self):
        self.assertEqual(self.decide(keys={}), HOLD)

    def test_expired_signature_holds(self):
        self.assertEqual(self.decide(now=self.now + 61), HOLD)

    def test_mismatched_plan_holds(self):
        self.assertEqual(self.decide(approval=self.sign(plan_sha256="0"*64)), HOLD)

    def test_missing_approval_holds(self):
        self.assertEqual(self.decide(approval={}), HOLD)

    def test_missing_trusted_policy_holds(self):
        self.assertEqual(self.decide(policy="synthetic_review"), HOLD)

    def test_mutable_policy_holds(self):
        self.assertEqual(self.decide(policy=PreflightPolicy({"synthetic_review"})), HOLD)

    def test_extra_request_fields_holds(self):
        self.assertEqual(self.decide(request={**self.request, "execute": True}), HOLD)

    def test_prohibited_set_has_side_effects(self):
        self.assertTrue({"run_command", "transfer_funds", "deploy_code"}.issubset(PROHIBITED))


if __name__ == "__main__":
    unittest.main()
