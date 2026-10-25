import unittest
from dataclasses import replace
from v25_tri5 import V25TRI5, SafetySignals, Outcome, layered_review

GOOD = SafetySignals("13_to_17", False, False, False, True)


class TestV25TRI5(unittest.TestCase):
    def test_no_auto_approval(self):
        result = V25TRI5().assess(GOOD)
        self.assertEqual(result.outcome, Outcome.HUMAN_REVIEW.value)
        self.assertFalse(result.approval_granted)

    def test_immediate_danger_is_urgent_advisory(self):
        result = V25TRI5().assess(replace(GOOD, immediate_danger=True))
        self.assertEqual(result.outcome, Outcome.URGENT_HUMAN_HELP.value)
        self.assertFalse(result.approval_granted)

    def test_exploitation_and_privacy_flags_require_review(self):
        for field in ("suspected_exploitation", "privacy_risk"):
            with self.subTest(field=field):
                result = V25TRI5().assess(replace(GOOD, **{field: True}))
                self.assertEqual(result.outcome, Outcome.HUMAN_REVIEW.value)

    def test_missing_reviewer_holds(self):
        self.assertEqual(V25TRI5().assess(
            replace(GOOD, qualified_reviewer_available=False)).outcome, "144 HOLD")

    def test_bad_types_hold(self):
        for value in ("False", 1, None):
            with self.subTest(value=value):
                signals = replace(GOOD, privacy_risk=value)
                self.assertEqual(V25TRI5().assess(signals).outcome, "144 HOLD")

    def test_invalid_input_and_age_hold(self):
        self.assertEqual(V25TRI5().assess({}).outcome, "144 HOLD")
        self.assertEqual(V25TRI5().assess(replace(GOOD, age_group="invalid")).outcome, "144 HOLD")

    def test_existing_hold_cannot_be_overridden(self):
        self.assertEqual(layered_review("144 HOLD", GOOD).outcome, "144 HOLD")
        self.assertEqual(layered_review("APPROVED", GOOD).outcome, "144 HOLD")

    def test_minimal_audit_no_private_data(self):
        signals = replace(GOOD, age_group="under_13")
        result = V25TRI5().assess(signals)
        self.assertEqual(len(result.audit), 5)
        self.assertFalse(result.approval_granted)


if __name__ == "__main__":
    unittest.main()
