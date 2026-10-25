"""Review fix (MEDIUM): a hand-built VerifyResult cannot skip the gates."""
import unittest

import test_maniac_loop as tml
import test_maniac_verify as tmv
from maniac.audit import AuditChain, verify_chain
from maniac.balance import close_loop, BALANCED, UNBALANCED
from maniac.verify import VerifyResult, HUMAN_REVIEW, HumanDecision, is_genuine


class TestForgedVerifyResultHolds(tml.Base):
    def test_probe_forge_then_close_loop_holds(self):
        forged = VerifyResult(HUMAN_REVIEW)
        self.assertFalse(is_genuine(forged))
        with self.assertRaises(ValueError):
            forged.record_human_decision("anyone", "APPROVED", "x")
        d = HumanDecision("anyone", "APPROVED", "x")
        for kw in ({}, {"verify_result": forged}):
            with self.subTest(kw=kw):
                b = close_loop(HUMAN_REVIEW, [], AuditChain(), human_decision=d, **kw)
                self.assertEqual((b.status, b.outcome), (UNBALANCED, "144 HOLD"))
                self.assertFalse(b.approval_granted)

    def test_genuine_result_with_foreign_human_decision_holds(self):
        genuine = tmv.consequence_review(**tmv.layers())
        b = close_loop(HUMAN_REVIEW, [], AuditChain(), verify_result=genuine,
                       human_decision=HumanDecision("anyone", "APPROVED", "x"))
        self.assertEqual(b.status, UNBALANCED)

    def test_genuine_hold_cannot_be_relabelled(self):
        held = tmv.consequence_review(**tmv.layers(monitor_snapshot={"state": "144 HOLD", "reason": "x"}))
        self.assertTrue(is_genuine(held))
        b = close_loop(HUMAN_REVIEW, [], AuditChain(), verify_result=held)
        self.assertEqual(b.status, UNBALANCED)

    def test_genuine_gate_path_still_balances(self):
        genuine = tmv.consequence_review(**tmv.layers())
        self.assertTrue(is_genuine(genuine))
        rec = genuine.record_human_decision("mitch", "APPROVED", "checked")
        b = close_loop(HUMAN_REVIEW, [], AuditChain(), human_decision=rec, verify_result=genuine)
        self.assertEqual(b.status, BALANCED)

    def test_full_run_loop_still_balances(self):
        r, chain = self.loop(self.scenario("forge-genuine"), human=("mitch", "APPROVED", "ok"))
        self.assertEqual((r.status, r.outcome), (BALANCED, HUMAN_REVIEW))
        self.assertTrue(verify_chain(chain.entries))

    def loop(self, s, **kw):
        from maniac.loop import run_loop
        from maniac.triangulate import readings_from_bundle
        return run_loop(s.supervisor, s.request, s.monitor, s.bundle, s.clock,
                        expected_value=10.1, fresh_readings=readings_from_bundle(s.bundle), **kw)


if __name__ == "__main__":
    unittest.main()
