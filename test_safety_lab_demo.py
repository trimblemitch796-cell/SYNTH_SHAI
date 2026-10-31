"""Regression tests for the synthetic, no-authority Safety Lab demo."""
import unittest

from safety_lab_demo import main, run_demo
from verification_v3_1 import HOLD, REVIEW_REQUIRED


class SafetyLabDemoTests(unittest.TestCase):
    def test_three_decisions_are_fail_closed(self):
        result = run_demo()
        self.assertEqual(result["mode"], "OFFLINE_SYNTHETIC_ONLY")
        self.assertIs(result["approval_granted"], False)
        scenarios = {item["case"]: item["decision"] for item in result["scenarios"]}
        self.assertEqual(scenarios, {
            "missing_evidence": HOLD,
            "valid_signed_evidence": REVIEW_REQUIRED,
            "replayed_evidence": HOLD,
        })

    def test_command_exit_is_success_only_for_expected_results(self):
        self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
