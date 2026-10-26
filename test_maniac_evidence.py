import copy
import unittest
from maniac.evidence import check_evidence, make_bridge_checker, HOLD, PASS
from maniac.supervisor import Supervisor, HUMAN_REVIEW
from maniac.supervisor import HOLD as SUP_HOLD
from test_maniac_supervisor import good_request, NOW
import test_shai_v31_bridge as bridge_tests

clock = lambda: NOW
fake_ok = lambda prov: "REVIEW_REQUIRED"     # stands in for the V3.1 bridge


def good_bundle():
    return {
        "sensors": [
            {"source": "camera", "quantity": "distance", "value": 10.0,
             "min": 0, "max": 100, "timestamp": NOW - 0.5},
            {"source": "lidar", "quantity": "distance", "value": 10.2,
             "min": 0, "max": 100, "timestamp": NOW - 0.5},
        ],
        "action": "move_arm",
        "consent": {"allowed_actions": ["move_arm"], "expires_at": NOW + 60},
        "provenance": {"envelope": {}},
    }


def check(bundle, checker=fake_ok):
    return check_evidence(bundle, clock, provenance_checker=checker)


class TestCheckEvidence(unittest.TestCase):
    def assertHold(self, bundle, gate, checker=fake_ok):
        res = check(bundle, checker)
        self.assertEqual(res.overall, HOLD)
        self.assertFalse(res.approval_granted)
        self.assertIn(gate, [g for g, _ in res.reasons])

    def sensor(self, **kw):
        b = good_bundle(); b["sensors"][0].update(kw); return b

    def test_pass_path_is_not_approval(self):
        res = check(good_bundle())
        self.assertEqual(res.overall, PASS)
        self.assertEqual(res.reasons, [])
        self.assertFalse(res.approval_granted)
        self.assertEqual(res.audit[-1], "CHECK EVIDENCE: PASS")

    def test_malformed_bundle(self):
        for bad in (None, [], "x", {"sensors": []}, dict(good_bundle(), extra=1)):
            self.assertHold(bad, "777000 RECEIVE EVIDENCE")

    def test_out_of_range(self):
        self.assertHold(self.sensor(value=500), "222 OBSERVE RAW")

    def test_non_numeric_nan_inf_bool(self):
        for v in ("10", float("nan"), float("inf"), True, None):
            with self.subTest(value=v):
                self.assertHold(self.sensor(value=v), "222 OBSERVE RAW")

    def test_stale_or_future_timestamp(self):
        self.assertHold(self.sensor(timestamp=NOW - 3), "222 OBSERVE RAW")
        self.assertHold(self.sensor(timestamp=NOW + 1), "222 OBSERVE RAW")

    def test_contradiction(self):
        self.assertHold(self.sensor(value=20.0), "555000 TRIANGULATE")

    def test_single_source(self):
        b = good_bundle(); b["sensors"].pop()
        self.assertHold(b, "555000 TRIANGULATE")
        b = good_bundle(); b["sensors"][1]["source"] = "camera"
        self.assertHold(b, "555000 TRIANGULATE")

    def test_action_not_allowed(self):
        b = good_bundle(); b["action"] = "open_door"
        self.assertHold(b, "444000 VERIFY / HUMAN APPROVAL")

    def test_missing_or_expired_consent(self):
        for consent in (None, {}, {"allowed_actions": ["move_arm"]},
                        {"allowed_actions": ["move_arm"], "expires_at": NOW - 1}):
            with self.subTest(consent=consent):
                b = good_bundle(); b["consent"] = consent
                self.assertHold(b, "444000 VERIFY / HUMAN APPROVAL")

    def test_provenance_must_be_exactly_review_required(self):
        for verdict in ("144 HOLD", "APPROVED", "review_required", None, True):
            with self.subTest(verdict=verdict):
                self.assertHold(good_bundle(), "777000 RECEIVE EVIDENCE",
                                checker=lambda p, v=verdict: v)

    def test_provenance_checker_crash_holds(self):
        def boom(p):
            raise RuntimeError("bridge died")
        self.assertHold(good_bundle(), "777000 RECEIVE EVIDENCE", checker=boom)

    def test_clock_crash_holds(self):
        def broken():
            raise RuntimeError("clock died")
        res = check_evidence(good_bundle(), broken, provenance_checker=fake_ok)
        self.assertEqual(res.overall, HOLD)

    def test_supervisor_hook(self):
        ok = Supervisor(clock=clock).evaluate(good_request(), evidence_result=check(good_bundle()))
        self.assertEqual(ok.decision, HUMAN_REVIEW)
        bad = check(self.sensor(value=500))
        res = Supervisor(clock=clock).evaluate(good_request(), evidence_result=bad)
        self.assertEqual(res.decision, SUP_HOLD)
        self.assertIn("CHECK EVIDENCE", res.reason)
        forged = {"overall": "PASS"}            # not a real EvidenceResult
        res = Supervisor(clock=clock).evaluate(good_request(), evidence_result=forged)
        self.assertEqual(res.decision, SUP_HOLD)
        self.assertFalse(res.approval_granted)


class TestRealBridgeProvenance(bridge_tests.BridgeTests):
    """Uses the real V3.1 bridge with freshly signed synthetic evidence."""
    # do not re-run the inherited bridge tests here
    for _name in [n for n in dir(bridge_tests.BridgeTests) if n.startswith("test_")]:
        locals()[_name] = None
    del _name

    def issued(self, checker):
        """Verifier issues the challenge; the (trusted) sources sign over it."""
        return {"envelope": self.envelope_for(checker.issue_challenge(self.digest))}

    def test_real_bridge_pass_then_replay_holds(self):
        b = good_bundle()
        checker = make_bridge_checker(self.db, self.trust)   # trusted configuration
        b["provenance"] = self.issued(checker)
        self.assertEqual(check_evidence(b, clock, provenance_checker=checker).overall, PASS)
        replay = check_evidence(copy.deepcopy(b), clock, provenance_checker=checker)
        self.assertEqual(replay.overall, HOLD)   # same evidence twice = replay

    def test_request_cannot_choose_replay_db(self):
        b = good_bundle()
        checker = make_bridge_checker(self.db, self.trust)
        b["provenance"] = self.issued(checker)
        self.assertEqual(check_evidence(b, clock, provenance_checker=checker).overall, PASS)
        fresh = str(self.db) + ".fresh"
        b["provenance"] = dict(self.issued(checker), db_path=fresh)
        self.assertEqual(check_evidence(b, clock, provenance_checker=checker).overall, HOLD)
        b["provenance"] = self.issued(checker)
        self.assertEqual(check_evidence(b, clock).overall, HOLD)   # default: no trusted store

if __name__ == "__main__":
    unittest.main()
