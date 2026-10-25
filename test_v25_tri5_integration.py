"""Synthetic integration tests: MANIAC -> USHAI -> V25 TRI5.

No network, real child data, actuation or automatic reporting.
"""
import unittest
from dataclasses import replace

from maniac.supervisor import HOLD, HUMAN_REVIEW, Supervisor
from test_maniac_supervisor import NOW, good_request
from ushai_catharsis import EthicalEvidence
from v25_tri5 import SafetySignals, V25TRI5, layered_review

CLEAR = SafetySignals("13_to_17", False, False, False, True)


class TestSafeguardingIntegration(unittest.TestCase):
    def supervisor(self, request):
        return Supervisor(clock=lambda: NOW).evaluate(request)

    def test_clean_path_requires_human_review_not_approval(self):
        upstream = self.supervisor(good_request("tri5-1"))
        self.assertEqual(upstream.decision, HUMAN_REVIEW)
        outcome = layered_review(upstream.decision, CLEAR)
        self.assertEqual(outcome.outcome, HUMAN_REVIEW)
        self.assertFalse(upstream.approval_granted)
        self.assertFalse(outcome.approval_granted)

    def test_maniac_fault_cannot_be_overridden(self):
        req = good_request("tri5-2")
        req["faults"] = ["overheat"]
        upstream = self.supervisor(req)
        self.assertEqual(upstream.decision, HOLD)
        self.assertEqual(layered_review(upstream.decision, CLEAR).outcome, HOLD)

    def test_ushai_harm_cannot_be_overridden(self):
        req = good_request("tri5-3")
        req["ethical_evidence"] = EthicalEvidence(
            True, True, True, False, True, True
        )
        upstream = self.supervisor(req)
        self.assertEqual(upstream.decision, HOLD)
        self.assertEqual(layered_review(upstream.decision, CLEAR).outcome, HOLD)

    def test_unauthorised_action_cannot_be_overridden(self):
        req = good_request("tri5-4")
        req["action"] = "unauthorised"
        upstream = self.supervisor(req)
        self.assertEqual(upstream.decision, HOLD)
        self.assertEqual(layered_review(upstream.decision, CLEAR).outcome, HOLD)

    def test_privacy_and_exploitation_flags_are_review_only(self):
        for flag in ("privacy_risk", "suspected_exploitation"):
            with self.subTest(flag=flag):
                upstream = self.supervisor(good_request("tri5-" + flag))
                outcome = layered_review(
                    upstream.decision, replace(CLEAR, **{flag: True})
                )
                self.assertEqual(outcome.outcome, HUMAN_REVIEW)
                self.assertFalse(outcome.approval_granted)

    def test_urgent_help_is_advisory_not_authorisation(self):
        upstream = self.supervisor(good_request("tri5-urgent"))
        outcome = layered_review(
            upstream.decision, replace(CLEAR, immediate_danger=True)
        )
        self.assertEqual(outcome.outcome, "URGENT_HUMAN_HELP")
        self.assertFalse(outcome.approval_granted)

    def test_prior_hold_stays_hold_even_with_urgent_flag(self):
        req = good_request("tri5-urgent-hold")
        req["heartbeats"] = [NOW - 100]
        upstream = self.supervisor(req)
        self.assertEqual(upstream.decision, HOLD)
        decision = layered_review(
            upstream.decision, replace(CLEAR, immediate_danger=True)
        )
        self.assertEqual(decision.outcome, HOLD)
        # Human emergency support must be available independently:
        urgent_advice = V25TRI5().assess(
            replace(CLEAR, immediate_danger=True)
        )
        self.assertEqual(urgent_advice.outcome, "URGENT_HUMAN_HELP")

    def test_unknown_upstream_outcomes_hold(self):
        for outcome in ("APPROVED", None, True, ""):
            with self.subTest(outcome=outcome):
                self.assertEqual(layered_review(outcome, CLEAR).outcome, HOLD)

    def test_invalid_child_signal_holds(self):
        upstream = self.supervisor(good_request("tri5-invalid"))
        outcome = layered_review(
            upstream.decision, replace(CLEAR, privacy_risk="False")
        )
        self.assertEqual(outcome.outcome, HOLD)


if __name__ == "__main__":
    unittest.main()
