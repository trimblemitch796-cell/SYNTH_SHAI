import os
import tempfile
import unittest

from maniac.simulation import signed_envelope, issued_envelope, sim_trust
from maniac.triangulate import readings_from_bundle, triangulate
from maniac.evidence import check_evidence
from shai.twin import ShaiTwin, approval_for, plan_digest, JOINTS, HEIGHT_CM, MOVED, HOLD, SAFE_LOCK
from ushai_catharsis import EthicalEvidence

GOOD = EthicalEvidence(True, True, True, False, False, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.n = 0
        self.db = os.path.join(self.tmp.name, "replay.sqlite")

    def twin(self, **kw):
        """Twin whose replay store is trusted configuration, not request data."""
        """Replay store and pinned keys are trusted configuration, not request data."""
        self._last_twin = ShaiTwin(replay_db=self.db, trust=sim_trust(), **kw)
        return self._last_twin

    def prov(self, twin=None):
        """Evidence signed over a challenge issued by the twin's verifier."""
        self.n += 1
        twin = twin or getattr(self, "_last_twin", None)
        try:
            return {"envelope": issued_envelope(twin)}
        except (AttributeError, ValueError):   # no verifier configured -> unissued challenge
            return {"envelope": signed_envelope("twin-test-unissued-%04d" % self.n)}

    def ask(self, twin, rid="r1", moves=None, secs=2.0, approve=True, approval=None,
            ethics=GOOD, prov="fresh"):
        plan = {"request_id": rid, "moves": moves or {"elbow_left": 30}, "duration_s": secs}
        if approval is None and approve:
            approval = approval_for(plan, "mitch", "APPROVED", "test")
        return twin.request_motion(plan, approval, self.prov(twin) if prov == "fresh" else prov, ethics)


class TestTwinBasics(Base):
    def test_example_body(self):
        self.assertEqual(HEIGHT_CM, 170)
        self.assertGreaterEqual(len(JOINTS), 5)
        self.assertTrue(all(v == 0.0 for v in self.twin().joint_angles.values()))

    def test_deterministic(self):
        self.assertEqual(self.twin(seed=3).sense(), self.twin(seed=3).sense())

    def test_sensor_readings_fit_maniac(self):
        t = self.twin()
        for _ in range(3):
            t.sense()
        bundle = t._bundle(self.prov())
        tri = triangulate(readings_from_bundle(bundle))
        self.assertEqual(tri.outcome, "PASS")
        self.assertEqual({r["source_type"] for r in readings_from_bundle(bundle)}, {"camera", "lidar"})
        self.assertEqual(check_evidence(bundle, t._clock,
                                        provenance_checker=t._supervisor.provenance_checker).overall, "PASS")


class TestMotionGate(Base):
    def test_approved_small_motion_moves(self):
        t = self.twin()
        r = self.ask(t)
        self.assertEqual(r.outcome, MOVED)
        self.assertEqual(t.joint_angles["elbow_left"], 30)
        self.assertFalse(r.approval_granted)
        self.assertTrue(r.balance.human_decision.approved)
        self.assertLess(t.power["energy_wh"], 2000)

    def test_consent_must_cover_entire_motion(self):
        t = self.twin(consent_seconds=0.05)
        before = t.power
        self.assertNoMove(t, self.ask(t, secs=2.0), "consent")
        self.assertEqual(t.power, before)

    def test_consent_rechecked_before_each_motion_step(self):
        t = self.twin()
        original_tick = t._tick
        ticks = 0

        def expire_during_motion():
            nonlocal ticks
            ticks += 1
            original_tick()
            if ticks == 2:  # initial request tick, then first movement tick
                t._consent_until = t._clock()

        t._tick = expire_during_motion
        result = self.ask(t)
        self.assertEqual(result.outcome, HOLD)
        self.assertTrue(result.moved)
        self.assertAlmostEqual(t.joint_angles["elbow_left"], 1.5)
        self.assertEqual(len(t.safe_stops), 1)
        self.assertIn("consent", result.reasons[0])

    def test_short_motion_uses_requested_duration(self):
        t = self.twin(consent_seconds=0.05)
        started = t._clock()
        result = self.ask(t, moves={"elbow_left": 1}, secs=0.04)
        self.assertEqual(result.outcome, MOVED)
        self.assertAlmostEqual(t._clock() - started, 0.04)

    def test_motion_can_finish_at_consent_deadline(self):
        t = self.twin(consent_seconds=2.0)
        result = self.ask(t, secs=2.0)
        self.assertEqual(result.outcome, MOVED)
        self.assertEqual(t._clock(), t._consent_until)

    def test_invalid_consent_duration_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, "1", None, -1, 10 ** 400):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.twin(consent_seconds=value)

    def assertNoMove(self, t, r, word, outcome=HOLD):
        self.assertEqual(r.outcome, outcome)
        self.assertFalse(r.moved)
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))
        self.assertTrue(any(word in x for x in r.reasons), r.reasons)

    def test_unapproved_holds(self):
        t = self.twin(); self.assertNoMove(t, self.ask(t, approve=False), "no human APPROVED")

    def test_rejected_holds(self):
        t = self.twin()
        r = self.ask(t, approval={"request_id": "r1", "operator_id": "mitch",
                                  "decision": "REJECTED", "reason": "no"})
        self.assertNoMove(t, r, "")

    def test_truthy_approval_holds(self):
        t = self.twin()
        r = self.ask(t, approval={"request_id": "r1", "operator_id": "mitch",
                                  "decision": True, "reason": "ok"})
        self.assertNoMove(t, r, "")

    def test_approval_for_other_request_holds(self):
        t = self.twin()
        r = self.ask(t, approval={"request_id": "other", "operator_id": "mitch",
                                  "decision": "APPROVED", "reason": "ok"})
        self.assertNoMove(t, r, "different request")

    def test_request_id_cannot_be_reused(self):
        t = self.twin()
        self.assertEqual(self.ask(t).outcome, MOVED)
        r = self.ask(t, moves={"elbow_left": 60})
        self.assertEqual(r.outcome, HOLD)
        self.assertEqual(t.joint_angles["elbow_left"], 30)

    def test_replayed_provenance_holds(self):
        t = self.twin()
        p = self.prov()
        self.assertEqual(self.ask(t, prov=p).outcome, MOVED)
        r = self.ask(t, rid="r2", moves={"elbow_left": 0}, prov=p)
        self.assertEqual(r.outcome, HOLD)
        self.assertEqual(t.joint_angles["elbow_left"], 30)

    def test_limits(self):
        cases = [({"elbow_left": 200}, 2.0, "outside limit"),
                 ({"elbow_left": 140}, 0.5, "over max"),
                 ({"tail": 10}, 2.0, "unknown joint"),
                 ({"elbow_left": float("nan")}, 2.0, "not a number"),
                 ({"elbow_left": "30"}, 2.0, "not a number")]
        for moves, secs, word in cases:
            with self.subTest(moves=moves):
                t = self.twin(); self.assertNoMove(t, self.ask(t, moves=moves, secs=secs), word)

    def test_malformed_plans(self):
        t = self.twin()
        for plan in (None, "go", {}, {"request_id": "x", "moves": {}, "duration_s": 1},
                     {"request_id": "x", "moves": {"elbow_left": 5}, "duration_s": 0},
                     {"request_id": "", "moves": {"elbow_left": 5}, "duration_s": 1},
                     {"request_id": "x", "moves": {"elbow_left": 5}, "duration_s": 1, "force": True}):
            with self.subTest(plan=plan):
                r = t.request_motion(plan, None, self.prov(), GOOD)
                self.assertEqual(r.outcome, HOLD)
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))

    def test_missing_ethics_or_provenance_holds(self):
        t = self.twin(); self.assertNoMove(t, self.ask(t, ethics=None), "")
        t = self.twin(); self.assertNoMove(t, self.ask(t, prov=None), "")

    def test_low_battery(self):
        t = self.twin(soc=0.10); self.assertNoMove(t, self.ask(t), "LOW_BATTERY")

    def test_not_enough_energy_above_reserve(self):
        t = self.twin(soc=0.0505)                    # 101 Wh: 1 Wh above reserve
        self.assertNoMove(t, self.ask(t, moves={"hip_left": 80, "hip_right": 80}), "reserve")

    def test_overheat_safe_lock(self):
        t = self.twin(temp_c=65.0)
        self.assertNoMove(t, self.ask(t), "SAFE_LOCK", outcome=SAFE_LOCK)

    def test_dropout_mid_motion_safe_stops(self):
        t = self.twin()
        t.inject_sensor_dropout("lidar", after_steps=5)
        r = self.ask(t)
        self.assertEqual(r.outcome, HOLD)
        angle = t.joint_angles["elbow_left"]
        self.assertTrue(0 < angle < 30)              # stopped part-way, at rest
        self.assertEqual(len(t.safe_stops), 1)
        # Nothing else moves afterwards: the monitor stays in HOLD
        r2 = self.ask(t, rid="r2", moves={"elbow_left": 0})
        self.assertEqual(r2.outcome, HOLD)
        self.assertEqual(t.joint_angles["elbow_left"], angle)


class TestNoBackdoor(Base):
    def test_joint_angles_is_a_copy(self):
        t = self.twin()
        t.joint_angles["elbow_left"] = 90
        self.assertEqual(t.joint_angles["elbow_left"], 0.0)

    def test_read_only_views(self):
        t = self.twin()
        for name in ("joint_angles", "power", "monitor_state", "safe_stops"):
            with self.subTest(name=name):
                with self.assertRaises(AttributeError):
                    setattr(t, name, {})

    def test_public_methods_never_move(self):
        t = self.twin()
        public = [m for m in dir(t) if not m.startswith("_") and callable(getattr(t, m))]
        self.assertEqual(sorted(public), ["inject_sensor_dropout", "issue_challenge", "request_motion",
                                          "safe_stop", "sense"])
        t.sense(); t.safe_stop("test"); t.inject_sensor_dropout("camera"); t.issue_challenge("a" * 64)
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))

    def test_result_frozen(self):
        t = self.twin()
        r = self.ask(t, approve=False)
        with self.assertRaises(AttributeError):
            r.outcome = MOVED
        with self.assertRaises(AttributeError):
            r.approval_granted = True



class TestReplayStoreIsTrustedConfig(Base):
    """Review finding (HIGH): the request must not choose the replay database."""

    def test_same_evidence_with_fresh_db_path_cannot_move_twin_again(self):
        t = self.twin()
        env = issued_envelope(t)
        self.assertEqual(self.ask(t, rid="x1", prov={"envelope": env}).outcome, MOVED)
        before = t.joint_angles
        fresh = os.path.join(self.tmp.name, "attacker-fresh.sqlite")
        r = self.ask(t, rid="x2", moves={"elbow_left": 0}, prov={"envelope": env, "db_path": fresh})
        self.assertEqual(r.outcome, HOLD)
        self.assertEqual(t.joint_angles, before)
        self.assertFalse(os.path.exists(fresh))     # never opened the attacker's DB

    def test_fresh_twin_same_store_rejects_replay(self):
        t1 = self.twin()
        env = issued_envelope(t1)
        self.assertEqual(self.ask(t1, rid="y1", prov={"envelope": env}).outcome, MOVED)
        t2 = self.twin()
        r = self.ask(t2, rid="y2", prov={"envelope": env})
        self.assertEqual(r.outcome, HOLD)
        self.assertTrue(all(v == 0.0 for v in t2.joint_angles.values()))

    def test_request_db_path_alone_is_refused(self):
        t = self.twin()
        fresh = os.path.join(self.tmp.name, "other.sqlite")
        r = self.ask(t, prov=dict(self.prov(), db_path=fresh))
        self.assertEqual(r.outcome, HOLD)
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))
        self.assertFalse(os.path.exists(fresh))

    def test_no_trusted_store_holds(self):
        t = ShaiTwin()                               # no replay_db configured
        r = self.ask(t)
        self.assertEqual(r.outcome, HOLD)
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))

    def test_bad_trusted_store_config_rejected(self):
        for bad in ("", 0, True, ["x"]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    ShaiTwin(replay_db=bad)



class TestApprovalBoundToExactPlan(Base):
    """Review finding (HIGH): approval must authorise one exact plan, once."""

    def plan(self, rid="r1", moves=None, secs=2.0):
        return {"request_id": rid, "moves": moves or {"elbow_left": 30}, "duration_s": secs}

    def go(self, t, plan, approval):
        return t.request_motion(plan, approval, self.prov(), GOOD)

    def test_small_elbow_approval_cannot_authorise_bigger_plan(self):
        small = self.plan()
        appr = approval_for(small, "mitch", "APPROVED", "small elbow move")
        t = self.twin()
        big = self.plan(moves={"elbow_left": 60, "knee_right": 20}, secs=4.0)
        r = self.go(t, big, appr)
        self.assertEqual(r.outcome, HOLD)
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))
        self.assertEqual(self.go(t, small, appr).outcome, MOVED)   # the approved plan still works

    def test_held_request_id_and_approval_cannot_be_reused_for_new_plan(self):
        t = self.twin()
        bad = self.plan(moves={"elbow_left": 999})
        appr = approval_for(bad, "mitch", "APPROVED", "x")
        self.assertEqual(self.go(t, bad, appr).outcome, HOLD)
        r = self.go(t, self.plan(moves={"elbow_left": 60}), appr)
        self.assertEqual(r.outcome, HOLD)
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))

    def test_id_only_approval_holds(self):
        t = self.twin()
        appr = {"request_id": "r1", "operator_id": "mitch", "decision": "APPROVED", "reason": "x"}
        self.assertEqual(self.go(t, self.plan(), appr).outcome, HOLD)
        self.assertEqual(t.joint_angles["elbow_left"], 0.0)

    def test_tampered_or_extra_approval_fields_hold(self):
        p = self.plan()
        good = approval_for(p, "mitch", "APPROVED", "x")
        for bad in (dict(good, plan_sha256="0" * 64), dict(good, plan_sha256=None),
                    dict(good, extra=1), dict(good, request_id="r2")):
            with self.subTest(bad=bad):
                t = self.twin()
                self.assertEqual(self.go(t, p, bad).outcome, HOLD)
                self.assertEqual(t.joint_angles["elbow_left"], 0.0)

    def test_approval_is_single_use(self):
        t = self.twin()
        p = self.plan()
        appr = approval_for(p, "mitch", "APPROVED", "x")
        self.assertEqual(self.go(t, p, appr).outcome, MOVED)
        before = t.joint_angles
        r = self.go(t, p, appr)                                  # replay same approval
        self.assertEqual(r.outcome, HOLD)
        self.assertEqual(t.joint_angles, before)

    def test_digest_is_canonical(self):
        a = {"request_id": "r", "moves": {"elbow_left": 1, "knee_left": 2}, "duration_s": 2.0}
        b = {"duration_s": 2.0, "moves": {"knee_left": 2, "elbow_left": 1}, "request_id": "r"}
        self.assertEqual(plan_digest(a), plan_digest(b))
        self.assertNotEqual(plan_digest(a), plan_digest(dict(a, duration_s=3.0)))


if __name__ == "__main__":
    unittest.main()
