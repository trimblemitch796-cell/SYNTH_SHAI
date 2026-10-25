import copy
import unittest
from maniac.supervisor import Supervisor, Gate, HOLD, HUMAN_REVIEW, USHAI_CONSCIENCE
from ushai_catharsis import EthicalEvidence

NOW = 1000.0


def good_request(rid="req-1"):
    return {
        "request_id": rid,
        "action": "move_arm",
        "requested_limits": {"speed": 0.5},
        "consent": {"allowed_actions": ["move_arm"], "limits": {"speed": 1.0}},
        "sensors": [
            {"source": "camera", "value": 10.0, "min": 0, "max": 100},
            {"source": "lidar", "value": 10.2, "min": 0, "max": 100},
        ],
        "heartbeats": [NOW - 0.5],
        "faults": [],
        "evidence_verdict": "REVIEW_REQUIRED",
        "ethical_evidence": EthicalEvidence(True, True, True, False, False, True),
    }


def sup():
    return Supervisor(clock=lambda: NOW)


def with_change(**kw):
    r = good_request()
    r.update(kw)
    return r


class TestSupervisor(unittest.TestCase):
    def assertHold(self, req, text=None):
        res = sup().evaluate(req)
        self.assertEqual(res.decision, HOLD)
        self.assertFalse(res.approval_granted)
        if text:
            self.assertIn(text, res.reason)
        return res

    def test_happy_path_is_human_review_only(self):
        res = sup().evaluate(good_request())
        self.assertEqual(res.decision, HUMAN_REVIEW)
        self.assertFalse(res.approval_granted)

    def test_audit_trail_order(self):
        res = sup().evaluate(good_request())
        expected = [USHAI_CONSCIENCE, Gate.PAUSE.value, Gate.IDENTIFY.value,
                    Gate.OBSERVE_RAW.value, Gate.DEFINE.value, Gate.RECORD.value,
                    Gate.RECEIVE_EVIDENCE.value, Gate.TRIANGULATE.value,
                    Gate.CHECK_LOOP.value, "CONSEQUENCE REVIEW: EVIDENCE SUFFICIENT",
                    Gate.VERIFY.value, Gate.RE_OBSERVE.value, Gate.COMPARE_LEARN.value,
                    Gate.AUDIT.value, Gate.BALANCE.value]
        self.assertEqual(res.audit, expected)

    def test_hold_branch_still_runs_post_gates(self):
        res = self.assertHold(with_change(faults=["overheat"]))
        self.assertEqual(res.audit[-5:], [Gate.HOLD.value, Gate.RE_OBSERVE.value,
                                          Gate.COMPARE_LEARN.value, Gate.AUDIT.value,
                                          Gate.BALANCE.value])
        self.assertNotIn(Gate.VERIFY.value, res.audit)

    def test_malformed_input(self):
        for bad in (None, [], "hi", 42):
            self.assertHold(bad)

    def test_unknown_field(self):
        self.assertHold(with_change(approve="yes"), "unknown field")

    def test_missing_field(self):
        r = good_request(); del r["consent"]
        self.assertHold(r, "missing field")

    def test_missed_heartbeat(self):
        self.assertHold(with_change(heartbeats=[NOW - 10]), "watchdog")
        self.assertHold(with_change(heartbeats=[]), "heartbeat")
        self.assertHold(with_change(heartbeats=[NOW + 5]), "watchdog")

    def test_active_fault(self):
        self.assertHold(with_change(faults=["motor_stall"]), "fault")

    def test_sensor_out_of_range(self):
        r = good_request(); r["sensors"][0]["value"] = 500
        self.assertHold(r, "out of range")

    def test_contradiction(self):
        r = good_request(); r["sensors"][1]["value"] = 50
        self.assertHold(r, "contradiction")

    def test_action_outside_consent(self):
        self.assertHold(with_change(action="open_door"), "consent")
        self.assertHold(with_change(requested_limits={"speed": 5.0}), "consent")
        self.assertHold(with_change(requested_limits={"force": 1.0}), "consent")

    def test_provenance_failed_or_missing(self):
        for v in (None, "144 HOLD", "APPROVED", True):
            self.assertHold(with_change(evidence_verdict=v), "provenance")

    def test_fewer_than_two_sources(self):
        r = good_request(); r["sensors"] = r["sensors"][:1]
        self.assertHold(r, "two")
        r = good_request(); r["sensors"][1]["source"] = "camera"
        self.assertHold(r, "two")

    def test_ushai_conscience_holds(self):
        bad = EthicalEvidence(True, True, True, False, True, True)
        self.assertHold(with_change(ethical_evidence=bad), "USHAI")
        self.assertHold(with_change(ethical_evidence=None), "USHAI")

    def test_repeated_request_is_loop(self):
        s = sup()
        self.assertEqual(s.evaluate(good_request()).decision, HUMAN_REVIEW)
        res = s.evaluate(good_request())
        self.assertEqual(res.decision, HOLD)
        self.assertIn("loop", res.reason)

    def test_exceptions_fail_closed(self):
        def broken_clock():
            raise RuntimeError("clock died")
        res = Supervisor(clock=broken_clock).evaluate(good_request())
        self.assertEqual(res.decision, HOLD)
        r = good_request(); r["sensors"][0]["value"] = "not a number"
        self.assertHold(r)

    def test_recovery_requires_fresh_request(self):
        s = sup()
        held = s.evaluate(with_change(faults=["overheat"]))
        self.assertEqual(held.decision, HOLD)
        same = with_change()  # same request id as the held one
        self.assertEqual(s.recover(held, same).decision, HOLD)
        fresh = good_request("req-2")
        res = s.recover(held, fresh)
        self.assertEqual(res.decision, HUMAN_REVIEW)
        self.assertFalse(res.approval_granted)
        self.assertEqual(res.audit[:2], [Gate.REPAIR.value, Gate.RECOVERY.value])

    def test_recover_only_from_hold(self):
        s = sup()
        ok = s.evaluate(good_request())
        self.assertEqual(s.recover(ok, good_request("req-3")).decision, HOLD)

    def test_maniac_simulation_fault_injection(self):
        """MANIAC_SIMULATION: every injected synthetic fault must end in HOLD."""
        def inject(name, fn):
            r = good_request("sim-" + name); fn(r); return r
        faults = {
            "fault": lambda r: r.update(faults=["sim"]),
            "stale_heartbeat": lambda r: r.update(heartbeats=[NOW - 99]),
            "sensor_high": lambda r: r["sensors"][0].update(value=1e9),
            "sensor_nan": lambda r: r["sensors"][0].update(value=float("nan")),
            "disagree": lambda r: r["sensors"][1].update(value=90),
            "one_source": lambda r: r["sensors"].pop(),
            "no_consent": lambda r: r["consent"].update(allowed_actions=[]),
            "no_provenance": lambda r: r.update(evidence_verdict=None),
            "extra_field": lambda r: r.update(override=True),
            "bad_sensor": lambda r: r["sensors"].append({"source": "x"}),
            "harm": lambda r: r.update(ethical_evidence=EthicalEvidence(
                True, True, True, False, True, True)),
        }
        for name, fn in faults.items():
            with self.subTest(fault=name):
                res = sup().evaluate(inject(name, fn))
                self.assertEqual(res.decision, HOLD)
                self.assertFalse(res.approval_granted)


if __name__ == "__main__":
    unittest.main()
