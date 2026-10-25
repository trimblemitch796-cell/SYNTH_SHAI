import unittest
from super_tool_v1 import run


class SuperToolTests(unittest.TestCase):
    def test_ask_is_research_prompt_not_invented_answer(self):
        result = run("ASK", "Why does concrete crack?")
        self.assertEqual(result.status, "HUMAN_REVIEW")
        self.assertIn("No model inference", result.output)
        self.assertFalse(result.approval_granted)

    def test_check_never_claims_evidence_verified(self):
        result = run("CHECK", "The sensor is accurate", evidence=["claim A"])
        self.assertEqual(result.status, "HUMAN_REVIEW")
        self.assertIn("Unverified", result.output)

    def test_build_is_only_a_draft(self):
        result = run("BUILD", "Plan offline tests")
        self.assertEqual(result.status, "HUMAN_REVIEW")
        self.assertIn("DRAFT FOR HUMAN REVIEW", result.output)

    def test_invalid_mode_holds(self):
        self.assertEqual(run("ACT", "anything").status, "144 HOLD")

    def test_empty_and_large_inputs_hold(self):
        for text in ("", "   ", "x" * 4001):
            self.assertEqual(run("ASK", text).status, "144 HOLD")

    def test_action_requests_hold(self):
        for request in ("Execute this", "deploy app", "transfer money now",
                        "control robot", "track child"):
            with self.subTest(request=request):
                self.assertEqual(run("BUILD", request).status, "144 HOLD")

    def test_safeguarding_flag_holds(self):
        self.assertEqual(run("ASK", "Help", child_safety_concern=True).status,
                         "144 HOLD")

    def test_bad_evidence_and_flag_hold(self):
        self.assertEqual(run("CHECK", "claim", evidence=[{}]).status, "144 HOLD")
        self.assertEqual(run("CHECK", "claim", child_safety_concern="False").status,
                         "144 HOLD")

    def test_never_grants_approval(self):
        for mode in ("ASK", "CHECK", "BUILD"):
            result = run(mode, "Help with research")
            self.assertFalse(result.approval_granted)
            self.assertTrue(result.human_review_required)


if __name__ == "__main__":
    unittest.main()
