import unittest
from maniac.monitor import Monitor
from maniac.supervisor import Supervisor, HOLD, HUMAN_REVIEW
from ushai_catharsis import State
from test_maniac_supervisor import good_request, NOW


class Clock:
    def __init__(self, t=NOW):
        self.t = t

    def __call__(self):
        return self.t


def healthy_monitor():
    clock = Clock()
    m = Monitor(clock, ["camera", "lidar"])
    beat_all(m)
    return m, clock


def beat_all(m):
    m.heartbeat("camera")
    m.heartbeat("lidar")
    m.kick()


class TestMonitor(unittest.TestCase):
    def test_starts_in_hold_then_healthy_is_monitor(self):
        m = Monitor(Clock(), ["camera", "lidar"])
        self.assertEqual(m.evaluate(), State.HOLD)
        beat_all(m)
        self.assertEqual(m.evaluate(), State.MONITOR)
        self.assertFalse(m.snapshot()["approval_granted"])

    def test_missed_heartbeat_holds(self):
        clock = Clock()
        m = Monitor(clock, ["camera", "lidar"], timeouts={"lidar": 5.0})
        beat_all(m)
        clock.t += 3          # camera (2 s) late, lidar (5 s) fine
        m.kick()
        self.assertEqual(m.evaluate(), State.HOLD)
        self.assertIn("camera", m.reason)

    def test_missed_watchdog_kick_holds(self):
        m, clock = healthy_monitor()
        clock.t += 1.5
        m.heartbeat("camera"); m.heartbeat("lidar")
        clock.t += 1.0        # kick now 2.5 s old
        self.assertEqual(m.evaluate(), State.HOLD)
        self.assertIn("watchdog", m.reason)

    def test_fault_holds_and_clear_needs_reason(self):
        m, _ = healthy_monitor()
        self.assertEqual(m.raise_fault("overheat"), State.HOLD)
        self.assertEqual(m.clear_fault("overheat", ""), State.HOLD)
        self.assertEqual(m.clear_fault("overheat", "fan replaced"), State.MONITOR)
        self.assertTrue(any("fan replaced" in a for a in m.audit))

    def test_critical_fault_safe_lock(self):
        m, _ = healthy_monitor()
        self.assertEqual(m.raise_fault("estop", critical=True), State.SAFE_LOCK)

    def test_repeated_fault_safe_lock(self):
        m, _ = healthy_monitor()
        for _ in range(2):
            m.raise_fault("slip")
            m.clear_fault("slip", "retry")
        self.assertEqual(m.evaluate(), State.MONITOR)
        self.assertEqual(m.raise_fault("slip"), State.SAFE_LOCK)

    def test_latch_survives_clearing(self):
        m, _ = healthy_monitor()
        m.raise_fault("estop", critical=True)
        m.clear_fault("estop", "button released")
        beat_all(m)
        self.assertEqual(m.evaluate(), State.SAFE_LOCK)

    def test_reset_refused_without_operator_or_reason(self):
        m, _ = healthy_monitor()
        m.raise_fault("estop", critical=True)
        m.clear_fault("estop", "released")
        for op, why in (("", "ok"), ("mitch", ""), (None, "ok"), ("mitch", None), ("  ", "x")):
            self.assertEqual(m.human_reset(op, why), State.SAFE_LOCK)

    def test_reset_goes_to_hold_then_monitor_after_fresh_beats(self):
        m, clock = healthy_monitor()
        m.raise_fault("estop", critical=True)
        m.clear_fault("estop", "released")
        self.assertEqual(m.human_reset("mitch", "checked arm by hand"), State.HOLD)
        clock.t += 0.1
        m.heartbeat("camera")
        self.assertEqual(m.evaluate(), State.HOLD)   # not a full set yet
        m.heartbeat("lidar")
        self.assertEqual(m.evaluate(), State.HOLD)   # watchdog not kicked yet
        m.kick()
        self.assertEqual(m.evaluate(), State.MONITOR)

    def test_malformed_input_fails_closed(self):
        m, _ = healthy_monitor()
        self.assertEqual(m.heartbeat("ghost"), State.HOLD)
        m2, _ = healthy_monitor()
        self.assertEqual(m2.raise_fault(None), State.HOLD)

    def test_exception_fails_closed_or_stays_locked(self):
        def broken():
            raise RuntimeError("clock died")
        m = Monitor(broken, ["camera"])
        self.assertEqual(m.evaluate(), State.HOLD)
        m.latched = True
        self.assertEqual(m.evaluate(), State.SAFE_LOCK)

    def test_audit_records_state_changes(self):
        m, _ = healthy_monitor()
        m.raise_fault("estop", critical=True)
        self.assertTrue(any("MONITOR -> SAFE_LOCK" in a for a in m.audit))

    def test_supervisor_holds_on_non_monitor_snapshot(self):
        m, _ = healthy_monitor()
        ok = Supervisor(clock=lambda: NOW).evaluate(good_request(), m.snapshot())
        self.assertEqual(ok.decision, HUMAN_REVIEW)
        m.raise_fault("overheat")
        res = Supervisor(clock=lambda: NOW).evaluate(good_request(), m.snapshot())
        self.assertEqual(res.decision, HOLD)
        self.assertIn("144 HOLD", res.reason)
        for bad in ({"state": "SAFE_LOCK"}, {}, "MONITOR", 1):
            r = Supervisor(clock=lambda: NOW).evaluate(good_request(), bad)
            self.assertEqual(r.decision, HOLD)
            self.assertFalse(r.approval_granted)

    def test_fault_injection_loop(self):
        """MANIAC_SIMULATION: each injected fault leaves MONITOR."""
        injections = {
            "late_camera": (lambda m, c: setattr(c, "t", c.t + 3), State.HOLD),
            "fault": (lambda m, c: m.raise_fault("x"), State.HOLD),
            "critical": (lambda m, c: m.raise_fault("x", critical=True), State.SAFE_LOCK),
            "unknown_beat": (lambda m, c: m.heartbeat(42), State.HOLD),
            "future_beat": (lambda m, c: setattr(c, "t", c.t - 10), State.HOLD),
            "repeat": (lambda m, c: [m.raise_fault("r") for _ in range(3)], State.SAFE_LOCK),
        }
        for name, (inject, expected) in injections.items():
            with self.subTest(fault=name):
                m, clock = healthy_monitor()
                inject(m, clock)
                self.assertEqual(m.evaluate(), expected)
                self.assertFalse(m.snapshot()["approval_granted"])


if __name__ == "__main__":
    unittest.main()
