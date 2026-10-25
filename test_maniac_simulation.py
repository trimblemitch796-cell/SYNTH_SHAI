import unittest
from unittest import mock
from maniac import simulation
from maniac.simulation import run_all, SCENARIOS, HOLD, SAFE_LOCK, REVIEW

# The words each scenario's reason must contain, so a HOLD is for the RIGHT cause
EXPECTED_CAUSE = {
    "dead_heartbeat": "missed heartbeat", "watchdog_timeout": "watchdog",
    "stuck_sensor": "stuck", "out_of_range": "out of range",
    "nan_reading": "NaN", "inf_reading": "inf", "stale_reading": "stale",
    "contradiction": "contradict", "single_source": "fewer than two",
    "missing_consent": "consent missing", "expired_consent": "expired",
    "action_outside_consent": "not inside human consent",
    "forged_provenance": "provenance", "tampered_provenance": "provenance",
    "replayed_evidence": "provenance", "malformed_input": "no sensor readings",
    "same_type_sources": "not independent", "repeated_fault": "SAFE_LOCK",
    "loop_recovery_replayed": "new V3.1 challenge", "loop_recovery_stale": "not newer",
    "loop_no_recovery": "NaN", "loop_reobserve_mismatch": "world does not match", "several_faults": "overheat",
}


class TestSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = {r["name"]: r for r in run_all()}

    def test_every_scenario_passes(self):
        failed = [n for n, r in self.report.items() if not r["passed"]]
        self.assertEqual(failed, [])

    def test_baseline_reaches_human_review(self):
        self.assertEqual(self.report["baseline"]["actual"], REVIEW)

    def test_every_fault_holds_or_locks(self):
        for name, r in self.report.items():
            if name in ("baseline", "loop_clean", "loop_recovery_fresh"):
                continue
            with self.subTest(scenario=name):
                self.assertIn(r["actual"], (HOLD, SAFE_LOCK))

    def test_repeated_fault_is_safe_lock(self):
        self.assertEqual(self.report["repeated_fault"]["actual"], SAFE_LOCK)

    def test_hold_is_for_the_injected_cause(self):
        for name, word in EXPECTED_CAUSE.items():
            with self.subTest(scenario=name):
                self.assertIn(word, self.report[name]["reason"])

    def test_required_faults_are_covered(self):
        self.assertEqual(set(EXPECTED_CAUSE) | {"baseline", "loop_clean", "loop_recovery_fresh"},
                         {s[0] for s in SCENARIOS})

    def test_clean_and_recovered_loops_are_balanced(self):
        for name in ("loop_clean", "loop_recovery_fresh"):
            with self.subTest(scenario=name):
                self.assertEqual(self.report[name]["actual"], REVIEW)
                self.assertTrue(self.report[name]["reason"].startswith("BALANCED"))

    def test_several_faults_lists_every_reason(self):
        reason = self.report["several_faults"]["reason"]
        for word in ("overheat", "NaN", "not inside human consent", "555000 TRIANGULATE"):
            self.assertIn(word, reason)

    def test_report_fields(self):
        for r in self.report.values():
            self.assertEqual(set(r), {"name", "fault", "expected", "actual", "reason", "passed"})

    def test_deterministic(self):
        again = {r["name"]: r for r in run_all()}
        self.assertEqual(again, self.report)

    def test_cli_exit_codes(self):
        with mock.patch("builtins.print"):
            self.assertEqual(simulation.main(), 0)
            broken = [("bad", "x", lambda s: None, HOLD)]   # baseline mislabelled
            with mock.patch.object(simulation, "SCENARIOS", broken):
                self.assertEqual(simulation.main(), 1)


if __name__ == "__main__":
    unittest.main()
