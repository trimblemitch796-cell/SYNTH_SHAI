import unittest
from dataclasses import replace
from ushai_catharsis import USHAICatharsis, EthicalEvidence, State

GOOD = EthicalEvidence(True, True, True, False, False, True)


class TestUSHAICatharsis(unittest.TestCase):
    def test_happy_path_review_required(self):
        g = USHAICatharsis()
        self.assertEqual(g.assess(GOOD), "REVIEW_REQUIRED")
        self.assertIn("444000 VERIFY", g.audit)
        self.assertFalse(g.approval_granted)

    def test_each_hold_reason(self):
        cases = {
            "Undefined intent": replace(GOOD, intent_defined=False),
            "Consent unverified": replace(GOOD, consent_verified=False),
            "Evidence unverified": replace(GOOD, evidence_verified=False),
            "Contradiction detected": replace(GOOD, contradiction_found=True),
            "Potential harmful consequence": replace(GOOD, harmful_consequence_found=True),
            "Unresolved uncertainty": replace(GOOD, uncertainty_resolved=False),
        }
        for reason, ev in cases.items():
            with self.subTest(reason=reason):
                g = USHAICatharsis()
                self.assertEqual(g.assess(ev), "144 HOLD")
                self.assertIn("144 HOLD: " + reason, g.audit)
                self.assertNotIn("444000 VERIFY", g.audit)

    def test_truthy_string_now_holds(self):
        g = USHAICatharsis()
        self.assertEqual(g.assess(replace(GOOD, contradiction_found="False")), "144 HOLD")
        self.assertEqual(g.assess(replace(GOOD, intent_defined="True")), "144 HOLD")
        self.assertEqual(g.assess(replace(GOOD, intent_defined=1)), "144 HOLD")

    def test_wrong_type_fails_closed(self):
        g = USHAICatharsis()
        for bad in (None, {}, "REVIEW_REQUIRED", object()):
            self.assertEqual(g.assess(bad), "144 HOLD")

    def test_state_does_not_leak(self):
        g = USHAICatharsis()
        g.assess(GOOD)
        self.assertEqual(g.assess(replace(GOOD, consent_verified=False)), "144 HOLD")
        self.assertEqual(g.state, State.HOLD)
        self.assertEqual(g.audit[0], "000 PAUSE / ASSESS")
        self.assertEqual(sum(a.startswith("000") for a in g.audit), 1)

    def test_both_branches_end_in_balance(self):
        for ev in (GOOD, replace(GOOD, intent_defined=False)):
            g = USHAICatharsis()
            g.assess(ev)
            self.assertEqual(g.audit[-4:], ["222000 RE-OBSERVE", "111000 COMPARE / LEARN",
                                            "999000 AUDIT", "Δ BALANCE"])

    def test_recovery_requires_fresh_assessment(self):
        g = USHAICatharsis()
        g.assess(replace(GOOD, evidence_verified=False))
        self.assertEqual(g.propose_recovery(), "REVERIFY_REQUIRED")
        self.assertEqual(g.state, State.HOLD)
        self.assertEqual(g.assess(GOOD), "REVIEW_REQUIRED")

    def test_recovery_not_allowed_from_review(self):
        g = USHAICatharsis()
        g.assess(GOOD)
        self.assertNotEqual(g.propose_recovery(), "REVERIFY_REQUIRED")


if __name__ == "__main__":
    unittest.main()
