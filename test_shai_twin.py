import os
import tempfile
import unittest

from maniac.simulation import signed_envelope
from maniac.triangulate import readings_from_bundle, triangulate
from maniac.evidence import check_evidence
from shai.twin import ShaiTwin, JOINTS, HEIGHT_CM, MOVED, HOLD, SAFE_LOCK
from ushai_catharsis import EthicalEvidence

GOOD = EthicalEvidence(True, True, True, False, False, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.n = 0

    def prov(self):
        self.n += 1
        return {"envelope": signed_envelope("twin-test-challenge-%04d-%s" % (self.n, id(self))),
                "db_path": os.path.join(self.tmp.name, "replay.sqlite")}

    def ask(self, twin, rid="r1", moves=None, secs=2.0, approve=True, approval=None,
            ethics=GOOD, prov="fresh"):
        plan = {"request_id": rid, "moves": moves or {"elbow_left": 30}, "duration_s": secs}
        if approval is None and approve:
            approval = {"request_id": rid, "operator_id": "mitch", "decision": "APPROVED",
                        "reason": "test"}
        return twin.request_motion(plan, approval, self.prov() if prov == "fresh" else prov, ethics)


class TestTwinBasics(Base):
    def test_example_body(self):
        self.assertEqual(HEIGHT_CM, 170)
        self.assertGreaterEqual(len(JOINTS), 5)
        self.assertTrue(all(v == 0.0 for v in ShaiTwin().joint_angles.values()))

    def test_deterministic(self):
        self.assertEqual(ShaiTwin(seed=3).sense(), ShaiTwin(seed=3).sense())

    def test_sensor_readings_fit_maniac(self):
        t = ShaiTwin()
        for _ in range(3):
            t.sense()
        bundle = t._bundle(self.prov())
        tri = triangulate(readings_from_bundle(bundle))
        self.assertEqual(tri.outcome, "PASS")
        self.assertEqual({r["source_type"] for r in readings_from_bundle(bundle)}, {"camera", "lidar"})
        self.assertEqual(check_evidence(bundle, t._clock).overall, "PASS")


class TestMotionGate(Base):
    def test_approved_small_motion_moves(self):
        t = ShaiTwin()
        r = self.ask(t)
        self.assertEqual(r.outcome, MOVED)
        self.assertEqual(t.joint_angles["elbow_left"], 30)
        self.assertFalse(r.approval_granted)
        self.assertTrue(r.balance.human_decision.approved)
        self.assertLess(t.power["energy_wh"], 2000)

    def assertNoMove(self, t, r, word, outcome=HOLD):
        self.assertEqual(r.outcome, outcome)
        self.assertFalse(r.moved)
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))
        self.assertTrue(any(word in x for x in r.reasons), r.reasons)

    def test_unapproved_holds(self):
        t = ShaiTwin(); self.assertNoMove(t, self.ask(t, approve=False), "no human APPROVED")

    def test_rejected_holds(self):
        t = ShaiTwin()
        r = self.ask(t, approval={"request_id": "r1", "operator_id": "mitch",
                                  "decision": "REJECTED", "reason": "no"})
        self.assertNoMove(t, r, "")

    def test_truthy_approval_holds(self):
        t = ShaiTwin()
        r = self.ask(t, approval={"request_id": "r1", "operator_id": "mitch",
                                  "decision": True, "reason": "ok"})
        self.assertNoMove(t, r, "")

    def test_approval_for_other_request_holds(self):
        t = ShaiTwin()
        r = self.ask(t, approval={"request_id": "other", "operator_id": "mitch",
                                  "decision": "APPROVED", "reason": "ok"})
        self.assertNoMove(t, r, "different request")

    def test_request_id_cannot_be_reused(self):
        t = ShaiTwin()
        self.assertEqual(self.ask(t).outcome, MOVED)
        r = self.ask(t, moves={"elbow_left": 60})
        self.assertEqual(r.outcome, HOLD)
        self.assertEqual(t.joint_angles["elbow_left"], 30)

    def test_replayed_provenance_holds(self):
        t = ShaiTwin()
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
                t = ShaiTwin(); self.assertNoMove(t, self.ask(t, moves=moves, secs=secs), word)

    def test_malformed_plans(self):
        t = ShaiTwin()
        for plan in (None, "go", {}, {"request_id": "x", "moves": {}, "duration_s": 1},
                     {"request_id": "x", "moves": {"elbow_left": 5}, "duration_s": 0},
                     {"request_id": "", "moves": {"elbow_left": 5}, "duration_s": 1},
                     {"request_id": "x", "moves": {"elbow_left": 5}, "duration_s": 1, "force": True}):
            with self.subTest(plan=plan):
                r = t.request_motion(plan, None, self.prov(), GOOD)
                self.assertEqual(r.outcome, HOLD)
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))

    def test_missing_ethics_or_provenance_holds(self):
        t = ShaiTwin(); self.assertNoMove(t, self.ask(t, ethics=None), "")
        t = ShaiTwin(); self.assertNoMove(t, self.ask(t, prov=None), "")

    def test_low_battery(self):
        t = ShaiTwin(soc=0.10); self.assertNoMove(t, self.ask(t), "LOW_BATTERY")

    def test_not_enough_energy_above_reserve(self):
        t = ShaiTwin(soc=0.0505)                    # 101 Wh: 1 Wh above reserve
        self.assertNoMove(t, self.ask(t, moves={"hip_left": 80, "hip_right": 80}), "reserve")

    def test_overheat_safe_lock(self):
        t = ShaiTwin(temp_c=65.0)
        self.assertNoMove(t, self.ask(t), "SAFE_LOCK", outcome=SAFE_LOCK)

    def test_dropout_mid_motion_safe_stops(self):
        t = ShaiTwin()
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
        t = ShaiTwin()
        t.joint_angles["elbow_left"] = 90
        self.assertEqual(t.joint_angles["elbow_left"], 0.0)

    def test_read_only_views(self):
        t = ShaiTwin()
        for name in ("joint_angles", "power", "monitor_state", "safe_stops"):
            with self.subTest(name=name):
                with self.assertRaises(AttributeError):
                    setattr(t, name, {})

    def test_public_methods_never_move(self):
        t = ShaiTwin()
        public = [m for m in dir(t) if not m.startswith("_") and callable(getattr(t, m))]
        self.assertEqual(sorted(public), ["inject_sensor_dropout", "request_motion", "safe_stop", "sense"])
        t.sense(); t.safe_stop("test"); t.inject_sensor_dropout("camera")
        self.assertTrue(all(v == 0.0 for v in t.joint_angles.values()))

    def test_result_frozen(self):
        t = ShaiTwin()
        r = self.ask(t, approve=False)
        with self.assertRaises(AttributeError):
            r.outcome = MOVED
        with self.assertRaises(AttributeError):
            r.approval_granted = True


if __name__ == "__main__":
    unittest.main()
