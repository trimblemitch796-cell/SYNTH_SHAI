import unittest
from maniac.verify import (consequence_review, HOLD, HUMAN_REVIEW, PENDING_GATES,
                           HOLD_NEXT_STEPS, VerifyResult)
from maniac.evidence import EvidenceResult
from maniac.triangulate import triangulate
from maniac.supervisor import Supervisor
from ushai_catharsis import USHAICatharsis, EthicalEvidence
from test_maniac_supervisor import good_request, NOW

GOOD_ETHICS = EthicalEvidence(True, True, True, False, False, True)


def ushai(ev=GOOD_ETHICS):
    g = USHAICatharsis(); g.assess(ev); return g


def layers(**changes):
    parts = {
        "ushai": ushai(),
        "monitor_snapshot": {"state": "MONITOR", "reason": "healthy"},
        "evidence_result": EvidenceResult("PASS"),
        "triangulation": triangulate([{"source_id": "c", "source_type": "camera", "value": 1.0},
                                      {"source_id": "l", "source_type": "lidar", "value": 1.0}]),
    }
    parts.update(changes)
    return parts


class TestConsequenceReview(unittest.TestCase):
    def assertHold(self, layer_word, **changes):
        res = consequence_review(**layers(**changes))
        self.assertEqual(res.decision, HOLD)
        self.assertFalse(res.approval_granted)
        self.assertEqual(res.next_steps, HOLD_NEXT_STEPS)
        self.assertTrue(any(layer_word in layer for layer, _ in res.reasons), res.reasons)

    def test_all_sufficient_goes_to_human_review(self):
        res = consequence_review(**layers())
        self.assertEqual(res.decision, HUMAN_REVIEW)
        self.assertFalse(res.approval_granted)
        self.assertEqual(res.pending_gates, PENDING_GATES)

    def test_ushai_hold(self):
        self.assertHold("USHAI", ushai=ushai(EthicalEvidence(True, False, True, False, False, True)))
        self.assertHold("USHAI", ushai=USHAICatharsis())        # never assessed
        self.assertHold("USHAI", ushai="REVIEW_REQUIRED")       # a string is not the gate

    def test_monitor_hold(self):
        self.assertHold("MONITOR", monitor_snapshot={"state": "SAFE_LOCK", "reason": "x"})
        self.assertHold("MONITOR", monitor_snapshot=None)

    def test_evidence_hold(self):
        bad = EvidenceResult("144 HOLD", [("777000 RECEIVE EVIDENCE", "forged")])
        self.assertHold("CHECK EVIDENCE", evidence_result=bad)
        self.assertHold("CHECK EVIDENCE", evidence_result={"overall": "PASS"})

    def test_triangulate_hold(self):
        self.assertHold("555000", triangulation=triangulate([]))
        self.assertHold("555000", triangulation=None)

    def test_supervisor_hold(self):
        held = Supervisor(clock=lambda: NOW).evaluate(dict(good_request(), faults=["x"]))
        self.assertHold("SUPERVISOR", supervisor_result=held)

    def test_hold_branch_also_lists_pending_gates(self):
        res = consequence_review(**layers(monitor_snapshot=None))
        self.assertEqual(res.pending_gates, PENDING_GATES)

    def test_multi_fault_collects_every_reason(self):
        res = consequence_review(
            ushai=ushai(EthicalEvidence(True, True, True, False, True, True)),
            monitor_snapshot={"state": "144 HOLD", "reason": "missed heartbeat: camera"},
            evidence_result=EvidenceResult("144 HOLD", [("222 OBSERVE RAW", "NaN"),
                                                       ("777000 RECEIVE EVIDENCE", "forged")]),
            triangulation=triangulate([]))
        layer_names = [layer for layer, _ in res.reasons]
        self.assertEqual(len(res.reasons), 5)
        for word in ("USHAI", "MONITOR", "222 OBSERVE RAW", "777000", "555000"):
            self.assertTrue(any(word in n for n in layer_names), word)

    def test_supervisor_review_hook(self):
        sup = Supervisor(clock=lambda: NOW)
        ok = sup.review(good_request(), {"state": "MONITOR"}, EvidenceResult("PASS"),
                        layers()["triangulation"])
        self.assertEqual(ok.decision, HUMAN_REVIEW)
        bad = Supervisor(clock=lambda: NOW).review("junk", None, None, None)
        self.assertEqual(bad.decision, HOLD)
        self.assertGreaterEqual(len(bad.reasons), 4)


class TestHumanDecision(unittest.TestCase):
    def review(self):
        return consequence_review(**layers())

    def test_only_explicit_human_decision_approves(self):
        res = self.review()
        d = res.record_human_decision("mitch", "APPROVED", "checked the arm path myself")
        self.assertTrue(d.approved)
        self.assertFalse(res.approval_granted)       # the machine result still never approves
        self.assertEqual(res.human_decision, d)

    def test_rejected(self):
        self.assertFalse(self.review().record_human_decision("mitch", "REJECTED", "too fast").approved)

    def test_invalid_operator_or_reason(self):
        for op, why in (("", "ok"), ("  ", "ok"), (None, "ok"), (True, "ok"), (1, "ok"),
                        ("mitch", ""), ("mitch", "   "), ("mitch", True), ("mitch", None)):
            with self.subTest(op=op, why=why):
                with self.assertRaises(ValueError):
                    self.review().record_human_decision(op, "APPROVED", why)

    def test_invalid_decision_words(self):
        for word in (True, "true", "yes", "approved", "Approve", "APPROVED ", 1, None):
            with self.subTest(word=word):
                with self.assertRaises(ValueError):
                    self.review().record_human_decision("mitch", word, "reason")

    def test_cannot_approve_a_hold(self):
        held = consequence_review(**layers(monitor_snapshot=None))
        with self.assertRaises(ValueError):
            held.record_human_decision("mitch", "APPROVED", "override")

    def test_only_one_decision(self):
        res = self.review()
        res.record_human_decision("mitch", "REJECTED", "no")
        with self.assertRaises(ValueError):
            res.record_human_decision("mitch", "APPROVED", "changed mind")

    def test_approval_granted_cannot_be_set_at_creation(self):
        with self.assertRaises(TypeError):
            VerifyResult(HUMAN_REVIEW, approval_granted=True)


class TestImmutableResults(unittest.TestCase):
    def test_results_cannot_be_flipped_to_approved(self):
        res = consequence_review(**layers())
        sup = Supervisor(clock=lambda: NOW).evaluate(good_request())
        for obj in (res, EvidenceResult("PASS"), sup):
            with self.subTest(obj=type(obj).__name__):
                with self.assertRaises(AttributeError):
                    obj.approval_granted = True
                self.assertFalse(obj.approval_granted)
        with self.assertRaises(AttributeError):
            res.decision = HUMAN_REVIEW
        with self.assertRaises(AttributeError):
            sup.decision = "APPROVED"

    def test_human_decision_cannot_be_overwritten_directly(self):
        res = consequence_review(**layers())
        with self.assertRaises(AttributeError):
            res.human_decision = "APPROVED"


class TestReasonDedup(unittest.TestCase):
    def test_monitor_reason_appears_once_in_order(self):
        snap = {"state": "144 HOLD", "reason": "missed heartbeat: camera"}
        res = Supervisor(clock=lambda: NOW).review(good_request(), snap,
                                                   EvidenceResult("PASS"), layers()["triangulation"])
        texts = [t for _, t in res.reasons]
        self.assertEqual(sum("missed heartbeat" in t for t in texts), 1)
        self.assertEqual(res.reasons[0], ("MONITOR SYSTEM", "missed heartbeat: camera"))

    def test_exact_repeats_removed(self):
        ev = EvidenceResult("144 HOLD", [("222 OBSERVE RAW", "NaN"), ("222 OBSERVE RAW", "NaN"),
                                         ("777000 RECEIVE EVIDENCE", "forged")])
        res = consequence_review(**layers(evidence_result=ev))
        self.assertEqual(res.reasons, [("CHECK EVIDENCE 222 OBSERVE RAW", "NaN"),
                                       ("CHECK EVIDENCE 777000 RECEIVE EVIDENCE", "forged")])

    def test_new_supervisor_reason_is_kept(self):
        held = Supervisor(clock=lambda: NOW).evaluate(dict(good_request(), faults=["overheat"]))
        res = consequence_review(**layers(supervisor_result=held))
        self.assertEqual([layer for layer, _ in res.reasons], ["SUPERVISOR"])


if __name__ == "__main__":
    unittest.main()
