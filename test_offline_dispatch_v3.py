"""Adversarial tests for the in-process synthetic dispatch boundary."""
import hashlib
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from offline_approval_v1 import HOLD, SIGNED_FIELDS, canonical
from offline_preflight_v3 import PreflightPolicy
from offline_dispatch_v3 import SIMULATED, dispatch_simulation


class OfflineDispatchTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = str(Path(tmp.name) / "approval.sqlite")
        self.key = Ed25519PrivateKey.generate()
        self.keys = {"operator": self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)}
        self.now = 200000
        self.request = {"request_id": "req1", "action": "synthetic_review",
                        "plan_sha256": hashlib.sha256(b"review").hexdigest()}
        self.policy = PreflightPolicy(frozenset({"synthetic_review"}))
        self.approval = self.sign()

    def sign(self, **updates):
        body = dict(self.request, operator_id="operator",
                    nonce="challenge-unique-1234", expires_at=self.now + 30)
        body.update(updates)
        body["signature"] = self.key.sign(
            canonical({k: body[k] for k in SIGNED_FIELDS})).hex()
        return body

    def dispatch(self, request=None, approval=None, **kwargs):
        return dispatch_simulation(
            self.request if request is None else request,
            self.approval if approval is None else approval,
            policy=kwargs.get("policy", self.policy),
            trusted_operator_keys=kwargs.get("keys", self.keys),
            trusted_database_path=kwargs.get("db", self.db),
            now=kwargs.get("now", self.now))

    def test_authorized_simulation_only(self):
        result = self.dispatch()
        self.assertEqual((result.decision, result.simulated_effect),
                         (SIMULATED, "synthetic_review_recorded"))

    def test_unsigned_request_cannot_dispatch(self):
        self.assertEqual(self.dispatch(approval={}).decision, HOLD)

    def test_replay_cannot_dispatch_twice(self):
        self.assertEqual(self.dispatch().decision, SIMULATED)
        self.assertEqual(self.dispatch().decision, HOLD)

    def test_new_nonce_same_request_cannot_dispatch(self):
        self.assertEqual(self.dispatch().decision, SIMULATED)
        self.assertEqual(self.dispatch(approval=self.sign(nonce="challenge-unique-5678")).decision, HOLD)

    def test_expired_approval_cannot_dispatch(self):
        self.assertEqual(self.dispatch(now=self.now + 31).decision, HOLD)

    def test_forged_signature_cannot_dispatch(self):
        approval = dict(self.approval, signature="00"*64)
        self.assertEqual(self.dispatch(approval=approval).decision, HOLD)

    def test_disabled_policy_cannot_dispatch(self):
        self.assertEqual(self.dispatch(policy=PreflightPolicy(frozenset())).decision, HOLD)

    def test_wrong_action_even_with_allowlist_cannot_dispatch(self):
        request = dict(self.request, action="run_command")
        policy = PreflightPolicy(frozenset({"run_command"}))
        signed = self.sign(action="run_command")
        self.assertEqual(self.dispatch(request=request, approval=signed, policy=policy).decision, HOLD)

    def test_unrecognized_action_even_if_policy_allows_cannot_dispatch(self):
        request = dict(self.request, action="unrecognized")
        policy = PreflightPolicy(frozenset({"unrecognized"}))
        signed = self.sign(action="unrecognized")
        self.assertEqual(self.dispatch(request=request, approval=signed, policy=policy).decision, HOLD)

    def test_reject_and_then_valid_preserves_approval(self):
        self.assertEqual(self.dispatch(policy=PreflightPolicy(frozenset())).decision, HOLD)
        self.assertEqual(self.dispatch().decision, SIMULATED)

    def test_bad_storage_cannot_dispatch(self):
        self.assertEqual(self.dispatch(db=":memory:").decision, HOLD)

    def test_no_trusted_keys_cannot_dispatch(self):
        self.assertEqual(self.dispatch(keys={}).decision, HOLD)

    def test_request_adds_callback_cannot_dispatch(self):
        invoked = []
        request = dict(self.request, callback=lambda: invoked.append(1))
        self.assertEqual(self.dispatch(request=request).decision, HOLD)
        self.assertEqual(invoked, [])

    def test_result_is_immutable(self):
        result = self.dispatch()
        with self.assertRaises(FrozenInstanceError):
            result.decision = "ALLOWED"

    def test_no_effect_on_denied_result(self):
        result = self.dispatch(approval={})
        self.assertEqual(result.simulated_effect, None)


if __name__ == "__main__":
    unittest.main()
