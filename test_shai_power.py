import unittest
from maniac.monitor import Monitor
from shai import power
from shai.power import PowerModel, CAPACITY_WH, RESERVE_WH


class Clock:
    t = 1000.0

    def __call__(self):
        return self.t


def healthy_monitor():
    m = Monitor(Clock(), ["power"])
    m.heartbeat("power"); m.kick()
    return m


class TestPower(unittest.TestCase):
    def test_full_pack(self):
        p = PowerModel()
        self.assertEqual(p.energy_wh, CAPACITY_WH)
        self.assertEqual(p.available_for_tasks(), CAPACITY_WH - RESERVE_WH)

    def test_bad_soc(self):
        for soc in (-0.1, 1.5, "1", True, None):
            with self.subTest(soc=soc):
                with self.assertRaises(ValueError):
                    PowerModel(soc=soc)

    def test_motion_energy(self):
        self.assertAlmostEqual(PowerModel.motion_energy_wh(10, 0.01, 36), 0.1 + power.IDLE_W * 0.01)

    def test_temperature_requires_finite_number(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, "25", None, 10 ** 400):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    PowerModel(temp_c=value)

    def test_invalid_task_draw_preserves_state(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, "1", None, -1, 10 ** 400):
            with self.subTest(value=value):
                p = PowerModel()
                before = (p.energy_wh, p.temp_c)
                self.assertFalse(p.draw_task(value))
                self.assertEqual((p.energy_wh, p.temp_c), before)

    def test_invalid_reserve_draw_and_cooling_preserve_state(self):
        for method in ("draw_reserve", "cool"):
            for value in (float("nan"), float("inf"), -float("inf"), True, "1", None, -1, 10 ** 400):
                with self.subTest(method=method, value=value):
                    p = PowerModel()
                    before = (p.energy_wh, p.temp_c)
                    with self.assertRaises(ValueError):
                        getattr(p, method)(value)
                    self.assertEqual((p.energy_wh, p.temp_c), before)

    def test_motion_energy_rejects_invalid_inputs(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, "1", None, 10 ** 400):
            for index in range(3):
                args = [10, 0.01, 1]
                args[index] = value
                with self.subTest(value=value, index=index):
                    with self.assertRaises(ValueError):
                        PowerModel.motion_energy_wh(*args)
        for args in ((10, -1, 1), (10, 1, -1), (1e308, 1e308, 1)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    PowerModel.motion_energy_wh(*args)

    def test_task_never_uses_reserve(self):
        p = PowerModel(soc=0.06)                    # 120 Wh: only 20 above reserve
        self.assertFalse(p.draw_task(50))
        self.assertTrue(p.draw_task(20))
        self.assertEqual(p.available_for_tasks(), 0.0)
        self.assertFalse(p.draw_task(0.01))
        for bad in (-1, "5", None, True):
            self.assertFalse(PowerModel().draw_task(bad))

    def test_reserve_for_safe_stop_only(self):
        p = PowerModel(soc=0.05)
        p.draw_reserve(10)
        self.assertAlmostEqual(p.energy_wh, RESERVE_WH - 10)
        p.draw_reserve(10_000)
        self.assertEqual(p.energy_wh, 0.0)          # never below empty

    def test_heat_and_cooling(self):
        p = PowerModel()
        p.draw_task(10)
        hot = p.temp_c
        self.assertGreater(hot, power.AMBIENT_C)
        p.cool(10)
        self.assertLess(p.temp_c, hot)
        self.assertGreater(p.temp_c, power.AMBIENT_C)

    def test_low_battery_fault_holds(self):
        m = healthy_monitor()
        PowerModel(soc=0.10).check(m)
        self.assertEqual(m.evaluate().value, "144 HOLD")
        self.assertIn("LOW_BATTERY", m.faults)

    def test_over_temp_safe_lock(self):
        m = healthy_monitor()
        PowerModel(temp_c=61).check(m)
        self.assertEqual(m.evaluate().value, "SAFE_LOCK")

    def test_fault_not_counted_as_repeat(self):
        m = healthy_monitor()
        p = PowerModel(soc=0.10)
        for _ in range(5):
            p.check(m)
        self.assertEqual(m.evaluate().value, "144 HOLD")   # not SAFE_LOCK
        self.assertEqual(m.fault_counts["LOW_BATTERY"], 1)

    def test_healthy_pack_raises_nothing(self):
        m = healthy_monitor()
        PowerModel().check(m)
        self.assertEqual(m.evaluate().value, "MONITOR")


if __name__ == "__main__":
    unittest.main()
