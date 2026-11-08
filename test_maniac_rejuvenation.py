"""Offline negative-path tests for Always Rejuvenation V0.1."""
import tempfile
import unittest
from dataclasses import replace

from maniac.chain import run_chain
from maniac.rejuvenation import (
    HOLD, OFFLINE, NONE, RECOVERY_PENDING, REVIEW_PENDING,
    RESTORATION_REVIEWED, RejuvenationPolicy,
)
from maniac.simulation import Scenario
from maniac.verify import HUMAN_REVIEW, VerifyResult


class RejuvenationTests(unittest.TestCase):
    def setUp(self):
        self.policy = RejuvenationPolicy()

    def genuine_review(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        s = Scenario("rejuvenation", tmp.name + "/sim.sqlite")
        result = run_chain(s.supervisor, s.request, s.monitor, s.bundle, s.clock)
        self.assertEqual(result.decision, HUMAN_REVIEW)
        return result

    def assert_not_running(self, snapshot):
        self.assertIn(snapshot.operational_state, (HOLD, OFFLINE))
        self.assertFalse(snapshot.approval_granted)
        self.assertFalse(snapshot.may_execute)
        self.assertFalse(self.policy.approval_granted)
        self.assertFalse(self.policy.may_execute)

    def test_initial_hold_and_immutable_snapshot_audit(self):
        s = self.policy.snapshot()
        self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
        self.assertIsInstance(s.audit, tuple)
        self.assert_not_running(s)

    def test_shutdown_never_refused_and_resets_pending(self):
        self.policy.request_recovery("operator", "synthetic repair")
        s = self.policy.shutdown("scheduled shutdown")
        self.assertEqual((s.operational_state, s.phase), (OFFLINE, NONE))
        self.assert_not_running(s)
        self.assertEqual(self.policy.shutdown(None).operational_state, OFFLINE)

    def test_catharsis_is_containment_not_rejuvenation(self):
        self.policy.shutdown("test")
        s = self.policy.catharsis("overload")
        self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
        self.assertTrue(any("not rejuvenation" in e for e in s.audit))
        self.assert_not_running(s)

    def test_missing_malformed_or_multiline_note_holds(self):
        for op, why in ((None, "repair"), ("operator", None),
                        ("operator", " "), (True, "repair"),
                        ("operator", "line1\nline2"), ("x" * 257, "repair")):
            with self.subTest(op=op, reason=why):
                p = RejuvenationPolicy()
                s = p.request_recovery(op, why)
                self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
                self.assertFalse(s.may_execute)

    def test_valid_recovery_is_only_pending(self):
        s = self.policy.request_recovery("operator", "synthetic reset")
        self.assertEqual((s.operational_state, s.phase), (HOLD, RECOVERY_PENDING))
        self.assert_not_running(s)

    def test_verification_without_recovery_holds(self):
        s = self.policy.verify(self.genuine_review())
        self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
        self.assert_not_running(s)

    def test_forged_or_failed_verification_holds(self):
        for bad in (None, "HUMAN_REVIEW", VerifyResult(HUMAN_REVIEW),
                    VerifyResult(HOLD)):
            with self.subTest(result=bad):
                p = RejuvenationPolicy()
                p.request_recovery("operator", "repair")
                s = p.verify(bad)
                self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
                self.assertFalse(s.may_execute)

    def test_genuine_verification_is_review_only(self):
        result = self.genuine_review()
        self.policy.request_recovery("operator", "repair")
        s = self.policy.verify(result)
        self.assertEqual((s.operational_state, s.phase), (HOLD, REVIEW_PENDING))
        self.assert_not_running(s)

    def test_approved_record_still_offline(self):
        result = self.genuine_review()
        self.policy.request_recovery("operator", "repair")
        self.policy.verify(result)
        result.record_human_decision("operator", "APPROVED", "offline check")
        s = self.policy.record_human_review(result)
        self.assertEqual((s.operational_state, s.phase),
                         (OFFLINE, RESTORATION_REVIEWED))
        self.assert_not_running(s)

    def test_rejected_record_returns_to_hold(self):
        result = self.genuine_review()
        self.policy.request_recovery("operator", "repair")
        self.policy.verify(result)
        result.record_human_decision("operator", "REJECTED", "insufficient")
        s = self.policy.record_human_review(result)
        self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
        self.assert_not_running(s)

    def test_unrecorded_review_cannot_pass(self):
        result = self.genuine_review()
        self.policy.request_recovery("operator", "repair")
        self.policy.verify(result)
        s = self.policy.record_human_review(result)
        self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
        self.assert_not_running(s)

    def test_preapproved_stale_result_cannot_skip_gates(self):
        result = self.genuine_review()
        result.record_human_decision("operator", "APPROVED", "old decision")
        self.policy.request_recovery("operator", "new repair")
        s = self.policy.verify(result)
        self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
        self.assert_not_running(s)

    def test_shutdown_invalidates_prior_verification(self):
        result = self.genuine_review()
        self.policy.request_recovery("operator", "repair")
        self.policy.verify(result)
        self.policy.shutdown("stop now")
        result.record_human_decision("operator", "APPROVED", "stale review")
        s = self.policy.record_human_review(result)
        self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
        self.assert_not_running(s)

    def test_wrong_result_or_repeat_review_holds(self):
        result = self.genuine_review()
        self.policy.request_recovery("operator", "repair")
        self.policy.verify(result)
        s = self.policy.record_human_review(VerifyResult(HUMAN_REVIEW))
        self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
        self.assert_not_running(s)

    def test_second_recovery_attempt_fails_closed(self):
        self.policy.request_recovery("operator", "repair")
        s = self.policy.request_recovery("operator", "repeat")
        self.assertEqual((s.operational_state, s.phase), (HOLD, NONE))
        self.assert_not_running(s)


if __name__ == "__main__":
    unittest.main()
