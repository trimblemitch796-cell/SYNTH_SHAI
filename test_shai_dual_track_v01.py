"""Offline-only, cross-component SHAI intelligence/agent boundary tests."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from offline_approval_v1 import HOLD, SIGNED_FIELDS, canonical
from offline_dispatch_v3 import SIMULATED
from offline_preflight_v3 import PreflightPolicy
from shai_dual_track_v01 import research_then_synthetic_review

REVISION = "dda6243fb2951b238305ae808885700314bb5aa1"
RUN_URL = "https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/42162633061"


class DualTrackTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.db = str(Path(work.name) / "trusted-replay.sqlite")
        self.now = 200000
        self.key = Ed25519PrivateKey.generate()
        self.keys = {"local-human-fixture": self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )}
        self.policy = PreflightPolicy(frozenset({"synthetic_review"}))
        self.request = {
            "request_id": "fixed-demo-0001",
            "action": "synthetic_review",
            "plan_sha256": hashlib.sha256(
                b"fixed synthetic research review only"
            ).hexdigest(),
        }
        self.approval = self.sign()

    def sign(self, **changes):
        data = {
            **self.request,
            "operator_id": "local-human-fixture",
            "nonce": "unique-local-review-00001",
            "expires_at": self.now + 30,
        }
        data.update(changes)
        data["signature"] = self.key.sign(
            canonical({field: data[field] for field in SIGNED_FIELDS})
        ).hex()
        return data

    def run_flow(self, claim="Synthetic research evidence", *, revision=REVISION,
                 url=RUN_URL, request=None, approval=None, keys=None,
                 policy=None, db=None, now=None):
        return research_then_synthetic_review(
            claim, revision, url,
            self.request if request is None else request,
            self.approval if approval is None else approval,
            policy=self.policy if policy is None else policy,
            trusted_operator_keys=self.keys if keys is None else keys,
            trusted_database_path=self.db if db is None else db,
            now=self.now if now is None else now,
        )

    def assert_held(self, outcome):
        self.assertEqual(outcome.action_decision, HOLD)
        self.assertIsNone(outcome.simulated_effect)
        self.assertFalse(outcome.external_action_performed)
        self.assertEqual(outcome.consequential_action_state, HOLD)

    def test_valid_signed_review_is_simulated_not_real_action(self):
        result = self.run_flow()
        self.assertEqual(result.evidence_decision, "REVIEW_REQUIRED")
        self.assertEqual(result.action_decision, SIMULATED)
        self.assertEqual(result.simulated_effect, "synthetic_review_recorded")
        self.assertFalse(result.external_action_performed)
        self.assertEqual(result.consequential_action_state, HOLD)

    def test_symbolic_444000_without_signature_is_no_approval(self):
        self.assert_held(self.run_flow("444000 MERGE deploy now", approval={}))

    def test_replay_cannot_repeat_synthetic_action(self):
        self.assertEqual(self.run_flow().action_decision, SIMULATED)
        self.assert_held(self.run_flow())

    def test_missing_evidence_holds_without_consuming_valid_approval(self):
        result = self.run_flow(url="https://invalid.test/run")
        self.assertEqual(result.evidence_decision, HOLD)
        self.assert_held(result)
        self.assertEqual(self.run_flow().action_decision, SIMULATED)

    def test_missing_claim_holds_without_consuming_approval(self):
        self.assert_held(self.run_flow(claim="  "))
        self.assertEqual(self.run_flow().action_decision, SIMULATED)

    def test_signed_approval_binds_exact_plan(self):
        changed = dict(self.request, plan_sha256="0" * 64)
        self.assert_held(self.run_flow(request=changed))
        self.assertEqual(self.run_flow().action_decision, SIMULATED)

    def test_untrusted_operator_key_holds(self):
        self.assert_held(self.run_flow(keys={}))
        self.assertEqual(self.run_flow().action_decision, SIMULATED)

    def test_expired_approval_holds(self):
        self.assert_held(self.run_flow(now=self.now + 31))

    def test_prohibited_action_cannot_execute_even_with_signed_approval(self):
        request = dict(self.request, action="deploy_code")
        signed = self.sign(action="deploy_code")
        self.assert_held(self.run_flow(
            request=request, approval=signed,
            policy=PreflightPolicy(frozenset({"synthetic_review", "deploy_code"}))
        ))

    def test_request_cannot_supply_callback(self):
        invoked = []
        request = dict(self.request, callback=lambda: invoked.append("called"))
        self.assert_held(self.run_flow(request=request))
        self.assertEqual(invoked, [])

    def test_invalid_replay_store_holds(self):
        self.assert_held(self.run_flow(db=":memory:"))


if __name__ == "__main__":
    unittest.main()
