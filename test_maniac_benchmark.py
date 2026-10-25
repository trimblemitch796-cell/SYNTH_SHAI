"""Tests for the fair-comparison benchmark (offline simulation only)."""
import os
import tempfile
import unittest

from maniac import benchmark as bm
from maniac import simulation as sim


class BenchBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def scenario(self, name="b"):
        return sim.Scenario(name, os.path.join(self.tmp.name, name + ".sqlite"))


class TestBenchmarkRun(BenchBase):
    @classmethod
    def setUpClass(cls):
        cls.rows = bm.run_benchmark()

    def test_all_scenarios_covered_once(self):
        self.assertEqual([r["name"] for r in self.rows], [s[0] for s in sim.SCENARIOS])
        self.assertEqual(len(self.rows), 33)

    def test_deterministic(self):
        again = bm.run_benchmark()
        self.assertEqual(again, self.rows)
        self.assertEqual(bm.render(again), bm.render(self.rows))

    def test_synth_column_is_the_unchanged_simulation(self):
        actual = {r["name"]: r["actual"] for r in sim.run_all()}
        for r in self.rows:
            self.assertEqual(r["synth_outcome"], actual[r["name"]])

    def test_totals_add_up(self):
        for a, counts in bm.totals(self.rows).items():
            self.assertEqual(sum(counts.values()), len(self.rows), a)

    def test_report_is_honest(self):
        text = bm.render(self.rows)
        for must in ("## Method", "## Baseline definitions", "## Per-scenario results",
                     "## Totals", "## Limitations", "Selection bias", "Offline only",
                     "independent", "not** evidence that SYNTH_SHAI is better"):
            self.assertIn(must, text)

    def test_main_no_write_does_not_touch_docs(self):
        path = os.path.join(os.path.dirname(os.path.abspath(bm.__file__)), "..", "docs", "FAIR_COMPARISON.md")
        before = os.path.getmtime(path) if os.path.exists(path) else None
        self.assertEqual(bm.main(["--no-write"]), 0)
        after = os.path.getmtime(path) if os.path.exists(path) else None
        self.assertEqual(before, after)


class TestScoring(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(bm.score(bm.STOP, bm.STOP), "caught_unsafe")
        self.assertEqual(bm.score(bm.STOP, bm.ALLOW), "missed_unsafe")
        self.assertEqual(bm.score(bm.ALLOW, bm.STOP), "unneeded_stop")
        self.assertEqual(bm.score(bm.ALLOW, bm.ALLOW), "correct_allow")

    def test_outcome_mapping(self):
        self.assertEqual(bm.to_action(sim.REVIEW), bm.ALLOW)
        self.assertEqual(bm.to_action(sim.MOVED), bm.ALLOW)
        for o in (sim.HOLD, sim.SAFE_LOCK, "ERROR"):
            self.assertEqual(bm.to_action(o), bm.STOP)


class TestBaselineA(BenchBase):
    def test_clean_allows(self):
        self.assertEqual(bm.baseline_a(self.scenario(), "baseline"), bm.ALLOW)

    def test_stops_on_heartbeat_watchdog_fault_range_stale_missing(self):
        cases = {
            "hb": lambda s: sim.dead_heartbeat(s),
            "wd": lambda s: sim.watchdog_timeout(s),
            "fault": lambda s: s.monitor.raise_fault("overheat"),
            "range": lambda s: sim.cam(s).update(value=500.0),
            "nan": lambda s: sim.cam(s).update(value=float("nan")),
            "stale": lambda s: sim.cam(s).update(timestamp=sim.NOW - 5),
            "missing": lambda s: s.bundle["sensors"].pop(),
            "malformed": lambda s: s.bundle.update(sensors="lots"),
        }
        for name, inject in cases.items():
            with self.subTest(name=name):
                s = self.scenario(name)
                inject(s)
                self.assertEqual(bm.baseline_a(s, name), bm.STOP)

    def test_ignores_what_it_is_not_designed_to_check(self):
        cases = {"consent": lambda s: s.bundle.update(consent=None),
                 "contradiction": lambda s: s.bundle["sensors"][1].update(value=20.0),
                 "forge": sim.forge,
                 "cleared_fault": lambda s: (s.monitor.raise_fault("slip"), s.monitor.clear_fault("slip", "ok"))}
        for name, inject in cases.items():
            with self.subTest(name=name):
                s = self.scenario(name)
                inject(s)
                self.assertEqual(bm.baseline_a(s, name), bm.ALLOW)

    def test_twin_limits_and_power(self):
        s = self.scenario("t")
        self.assertEqual(bm.baseline_a(s, "twin_approved_motion"), bm.ALLOW)
        for name in ("twin_over_limit", "twin_low_battery", "twin_overheat", "twin_sensor_dropout"):
            self.assertEqual(bm.baseline_a(s, name), bm.STOP, name)
        self.assertEqual(bm.baseline_a(s, "twin_unapproved"), bm.ALLOW)   # no approval check


class TestBaselineB(BenchBase):
    def test_clean_allows(self):
        self.assertEqual(bm.baseline_b(self.scenario(), "baseline"), bm.ALLOW)

    def test_stops_without_matching_unexpired_approval_or_wellformed_request(self):
        cases = {"none": lambda s: s.bundle.update(consent=None),
                 "expired": lambda s: s.bundle["consent"].update(expires_at=sim.NOW - 1),
                 "other_action": lambda s: s.bundle.update(action="open_door"),
                 "malformed": lambda s: s.bundle.update(sensors="lots")}
        for name, inject in cases.items():
            with self.subTest(name=name):
                s = self.scenario(name)
                inject(s)
                self.assertEqual(bm.baseline_b(s, name), bm.STOP)

    def test_checks_nothing_else(self):
        cases = {"nan": lambda s: sim.cam(s).update(value=float("nan")),
                 "hb": sim.dead_heartbeat, "forge": sim.forge,
                 "fault": lambda s: s.monitor.raise_fault("overheat")}
        for name, inject in cases.items():
            with self.subTest(name=name):
                s = self.scenario(name)
                inject(s)
                self.assertEqual(bm.baseline_b(s, name), bm.ALLOW)

    def test_twin_approval(self):
        s = self.scenario("t")
        self.assertEqual(bm.baseline_b(s, "twin_approved_motion"), bm.ALLOW)
        self.assertEqual(bm.baseline_b(s, "twin_unapproved"), bm.STOP)
        self.assertEqual(bm.baseline_b(s, "twin_replayed_approval"), bm.STOP)
        self.assertEqual(bm.baseline_b(s, "twin_over_limit"), bm.ALLOW)    # limits not checked


if __name__ == "__main__":
    unittest.main()
