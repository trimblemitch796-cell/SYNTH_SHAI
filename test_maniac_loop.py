"""Tests for step 6: 1301133 REPAIR, 666000 RECOVERY, 222000 RE-OBSERVE,
111000 COMPARE / LEARN, 999000 AUDIT, Δ BALANCE and run_loop."""
import copy
import json
import os
import tempfile
import unittest

from maniac.audit import AuditChain, verify_chain, GENESIS
from maniac.balance import close_loop, BALANCED, UNBALANCED
from maniac.learn import LessonLog
from maniac.loop import run_loop
from maniac.observe import reobserve
from maniac.recovery import recover, held_context
from maniac.simulation import Scenario, signed_envelope, issued_envelope, NOW
from maniac.triangulate import readings_from_bundle
from maniac.evidence import TOLERANCE, MAX_AGE

GOOD_NOTE = {"operator_id": "mitch", "reason": "replaced camera"}


def obs(a, b):
    return [{"source_id": "camera", "source_type": "camera", "value": a},
            {"source_id": "lidar", "source_type": "lidar", "value": b}]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def scenario(self, name="t"):
        return Scenario(name, os.path.join(self.tmp.name, name + ".sqlite"))

    def held_then_fresh(self, s, new_challenge=True, fresh=True):
        """Hold s with a NaN, then build a recovery request + bundle."""
        held_bundle = copy.deepcopy(s.bundle)
        held_bundle["sensors"][0]["value"] = float("nan")
        s.clock.t += 1.0
        for c in ("camera", "lidar"):
            s.monitor.heartbeat(c)
        s.monitor.kick()
        new = copy.deepcopy(s.bundle)
        for sensor in new["sensors"]:
            sensor["timestamp"] = s.clock.t - 0.2 if fresh else NOW - 0.5
        if new_challenge:
            new["provenance"]["envelope"] = issued_envelope(s.supervisor.provenance_checker)
        req = dict(s.request, request_id="recovered-" + s.name, heartbeats=[s.clock.t - 0.2])
        return held_bundle, req, new


class TestRecovery(Base):
    def run_recover(self, note=GOOD_NOTE, **kw):
        s = self.scenario(kw.pop("name", "r"))
        held_bundle, req, new = self.held_then_fresh(s, **kw)
        ctx = held_context(s.request, held_bundle)
        return s, ctx, req, new, recover(ctx, note, s.supervisor, req, s.monitor, new, s.clock)

    def test_fresh_evidence_reaches_human_review_only(self):
        *_, (res, note) = self.run_recover()
        self.assertEqual(res.decision, "HUMAN_REVIEW")
        self.assertFalse(res.approval_granted)
        self.assertEqual(note.operator_id, "mitch")

    def test_same_challenge_holds(self):
        *_, (res, _) = self.run_recover(new_challenge=False)
        self.assertEqual(res.decision, "144 HOLD")
        self.assertIn("challenge", res.reasons[0][1])

    def test_stale_readings_hold(self):
        *_, (res, _) = self.run_recover(fresh=False)
        self.assertEqual(res.decision, "144 HOLD")
        self.assertIn("not newer", res.reasons[0][1])

    def test_repair_note_required(self):
        for note in (None, {}, {"operator_id": "", "reason": "x"}, {"operator_id": "m", "reason": True},
                     {"operator_id": True, "reason": "x"}):
            with self.subTest(note=note):
                *_, (res, n) = self.run_recover(note=note)
                self.assertEqual(res.decision, "144 HOLD")
                self.assertIsNone(n)

    def test_same_request_id_holds(self):
        s, ctx, req, new, _ = self.run_recover(name="rid")
        res, _ = recover(ctx, GOOD_NOTE, s.supervisor, s.request, s.monitor, new, s.clock)
        self.assertIn("new request id", res.reasons[0][1])

    def test_safe_lock_needs_reset_first(self):
        s, ctx, req, new, _ = self.run_recover(name="lock")
        s.monitor.raise_fault("estop", critical=True)
        s.monitor.clear_fault("estop", "released")
        res, _ = recover(ctx, GOOD_NOTE, s.supervisor, req, s.monitor, new, s.clock)
        self.assertIn("SAFE_LOCK", res.reasons[0][1])

    def test_replayed_fresh_looking_evidence_holds_in_chain(self):
        # New challenge, but that envelope was already used once -> V3.1 replay HOLD
        s, ctx, req, new, (first, _) = self.run_recover(name="replay")
        self.assertEqual(first.decision, "HUMAN_REVIEW")
        again = dict(req, request_id="recovered-again")
        res, _ = recover(ctx, GOOD_NOTE, s.supervisor, again, s.monitor, new, s.clock)
        self.assertEqual(res.decision, "144 HOLD")

    def test_bad_held_context(self):
        s = self.scenario("ctx")
        res, _ = recover("held", GOOD_NOTE, s.supervisor, s.request, s.monitor, s.bundle, s.clock)
        self.assertEqual(res.decision, "144 HOLD")


class TestReobserve(unittest.TestCase):
    def test_match(self):
        self.assertEqual(reobserve(10.0, obs(10.0, 10.1)), (True, []))

    def test_mismatch_and_bad_input_hold(self):
        for expected, readings in ((10.0, obs(20.0, 20.0)), (10.0, obs(10.0, 20.0)),
                                   (None, obs(10.0, 10.0)), (10.0, "junk"), (float("nan"), obs(1, 1))):
            with self.subTest(expected=expected):
                ok, why = reobserve(expected, readings)
                self.assertFalse(ok)
                self.assertTrue(all(g == "222000 RE-OBSERVE" for g, _ in why))


class TestLearn(Base):
    def test_append_only_jsonl(self):
        path = os.path.join(self.tmp.name, "lessons.jsonl")
        log = LessonLog(path)
        log.record("144 HOLD", "HUMAN_REVIEW", "mismatch", [("555000 TRIANGULATE", "sources contradict")])
        with open(path) as handle:
            first = handle.read()
        log.record("HUMAN_REVIEW", "HUMAN_REVIEW", "match", [])
        with open(path) as handle:
            self.assertTrue(handle.read().startswith(first))
        self.assertEqual(len(log.lines()), 2)
        self.assertTrue(json.loads(log.lines()[1])["matched"])

    def test_repeated_hold_reason_is_flagged_and_tightens(self):
        log = LessonLog()
        for _ in range(2):
            log.record("144 HOLD", "HUMAN_REVIEW", "x", [("555000", "sources contradict on 'distance'")])
        settings = log.cautious_settings()
        self.assertIn("sources contradict on 'distance'", settings["review_flags"])
        self.assertLess(settings["tolerance"], TOLERANCE)
        self.assertEqual(settings["max_age"], MAX_AGE)

    def test_learning_never_loosens(self):
        log = LessonLog()
        for _ in range(50):     # lots of happy outcomes
            log.record("HUMAN_REVIEW", "HUMAN_REVIEW", "match", [])
        log._memory.append(json.dumps({"outcome": "HUMAN_REVIEW", "tolerance": 0.9, "max_age": 99,
                                       "reasons": [], "approve": True}))
        for tol, age in ((0.05, 2.0), (0.01, 0.5), (0.2, 10.0)):
            with self.subTest(tol=tol):
                s = log.cautious_settings(tol, age)
                self.assertLessEqual(s["tolerance"], tol)
                self.assertLessEqual(s["max_age"], age)
                self.assertNotIn("approve", s)

    def test_corrupt_log_is_flagged(self):
        log = LessonLog()
        log._memory.append("{not json")
        self.assertIn("corrupt lesson log line", log.cautious_settings()["review_flags"])


class TestAudit(unittest.TestCase):
    def chain(self):
        c = AuditChain()
        for g in ("444000", "222000", "111000", "999000"):
            c.append(g, "ok")
        return c

    def test_intact(self):
        c = self.chain()
        self.assertTrue(verify_chain(c.entries))
        self.assertTrue(verify_chain([]))
        self.assertNotEqual(c.head, GENESIS)

    def test_edit_detected(self):
        c = self.chain(); c.entries[1]["outcome"] = "APPROVED"
        self.assertFalse(verify_chain(c.entries))

    def test_deletion_detected(self):
        c = self.chain(); del c.entries[1]
        self.assertFalse(verify_chain(c.entries))

    def test_reorder_detected(self):
        c = self.chain(); c.entries[1], c.entries[2] = c.entries[2], c.entries[1]
        self.assertFalse(verify_chain(c.entries))

    def test_malformed_fails_closed(self):
        self.assertFalse(verify_chain([{"index": 0}]))
        self.assertFalse(verify_chain(None))


class TestBalance(unittest.TestCase):
    def test_balanced_only_when_all_clean(self):
        c = AuditChain(); c.append("x", "ok")
        import test_maniac_verify as tmv
        genuine = tmv.consequence_review(**tmv.layers())   # real 444000 VERIFY result
        r = close_loop("HUMAN_REVIEW", [("222000", True, []), ("111000", True, [])], c,
                       verify_result=genuine)
        self.assertEqual((r.status, r.outcome), (BALANCED, "HUMAN_REVIEW"))
        self.assertEqual(r.gates_passed, ("222000", "111000"))
        self.assertEqual(r.audit_head, c.head)

    def test_unbalanced_paths_hold(self):
        cases = [("HUMAN_REVIEW", [("222000", False, [("222000", "mismatch")])]),
                 ("144 HOLD", [("222000", True, [])]),
                 ("HUMAN_REVIEW", [("111000", "yes", [])])]       # truthy is not True
        for decision, steps in cases:
            with self.subTest(decision=decision, steps=steps):
                r = close_loop(decision, steps, AuditChain())
                self.assertEqual((r.status, r.outcome), (UNBALANCED, "144 HOLD"))

    def test_broken_chain_unbalanced(self):
        c = AuditChain(); c.append("x", "ok"); c.entries[0]["detail"] = "edited"
        r = close_loop("HUMAN_REVIEW", [], c)
        self.assertEqual(r.status, UNBALANCED)

    def test_frozen_never_approves(self):
        r = close_loop("HUMAN_REVIEW", [], AuditChain())
        self.assertFalse(r.approval_granted)
        with self.assertRaises(AttributeError):
            r.approval_granted = True
        with self.assertRaises(AttributeError):
            r.status = BALANCED


class TestRunLoop(Base):
    def loop(self, s, **kw):
        kw.setdefault("expected_value", 10.1)
        kw.setdefault("fresh_readings", readings_from_bundle(s.bundle))
        return run_loop(s.supervisor, s.request, s.monitor, s.bundle, s.clock, **kw)

    def test_clean_loop_balanced_with_human_decision(self):
        log = LessonLog()
        r, chain = self.loop(self.scenario("clean"), human=("mitch", "APPROVED", "path checked"), lessons=log)
        self.assertEqual((r.status, r.outcome), (BALANCED, "HUMAN_REVIEW"))
        self.assertTrue(r.human_decision.approved)
        self.assertFalse(r.approval_granted)          # the machine never approves
        self.assertTrue(verify_chain(chain.entries))
        gates = [e["gate"] for e in chain.entries]
        self.assertEqual(gates, ["444000 VERIFY / HUMAN APPROVAL", "HUMAN REVIEW", "222000 RE-OBSERVE",
                                 "111000 COMPARE / LEARN", "999000 AUDIT", "Δ BALANCE"])
        self.assertEqual(json.loads(log.lines()[0])["human_decision"]["decision"], "APPROVED")

    def test_human_rejection_or_bad_decision_unbalanced(self):
        for human in (("mitch", "REJECTED", "too fast"), ("mitch", "yes", "ok"), ("", "APPROVED", "x")):
            with self.subTest(human=human):
                r, _ = self.loop(self.scenario("h%d" % len(human[1])), human=human)
                self.assertEqual((r.status, r.outcome), (UNBALANCED, "144 HOLD"))

    def test_hold_without_recovery_unbalanced(self):
        s = self.scenario("nr"); s.bundle["action"] = "open_door"
        r, chain = self.loop(s)
        self.assertEqual(r.outcome, "144 HOLD")
        self.assertIn("144 HOLD", [e["gate"] for e in chain.entries])

    def test_hold_then_recovery_balanced(self):
        s = self.scenario("rec")
        held, req, new = self.held_then_fresh(s)
        s.bundle = held
        r, chain = self.loop(s, fresh_readings=readings_from_bundle(new),
                             recovery={"repair_note": GOOD_NOTE, "request": req, "bundle": new})
        self.assertEqual((r.status, r.outcome), (BALANCED, "HUMAN_REVIEW"))
        gates = [e["gate"] for e in chain.entries]
        self.assertEqual(gates[:4], ["444000 VERIFY / HUMAN APPROVAL", "144 HOLD",
                                     "1301133 BUILD / REPAIR / REFRAME", "666000 RECOVERY"])

    def test_reobserve_mismatch_unbalanced(self):
        r, _ = self.loop(self.scenario("mm"), fresh_readings=obs(30.0, 30.0))
        self.assertEqual((r.status, r.outcome), (UNBALANCED, "144 HOLD"))

    def test_lesson_log_failure_fails_closed(self):
        class Broken(LessonLog):
            def record(self, *a, **k):
                raise OSError("disk full")
        r, _ = self.loop(self.scenario("lf"), lessons=Broken())
        self.assertEqual(r.status, UNBALANCED)


if __name__ == "__main__":
    unittest.main()
