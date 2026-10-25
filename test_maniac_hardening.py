"""Regression tests for fail-closed MANIAC numeric and consent inputs."""
import unittest

from maniac.supervisor import HOLD, HUMAN_REVIEW, Supervisor
from test_maniac_supervisor import NOW, good_request


class HardenedSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.supervisor = Supervisor(clock=lambda: NOW)

    def check_hold(self, modifier):
        request = good_request("hardening-" + modifier.__name__)
        modifier(request)
        result = self.supervisor.evaluate(request)
        self.assertEqual(result.decision, HOLD)
        self.assertFalse(result.approval_granted)

    def test_nonfinite_sensor_values_hold(self):
        for v in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(v=str(v)):
                request = good_request("sensor-nonfinite")
                request["sensors"][0]["value"] = v
                self.assertEqual(Supervisor(clock=lambda: NOW).evaluate(request).decision, HOLD)

    def test_nonfinite_sensor_bounds_hold(self):
        for key in ("min", "max"):
            request = good_request("sensor-bound-" + key)
            request["sensors"][0][key] = float("inf")
            self.assertEqual(Supervisor(clock=lambda: NOW).evaluate(request).decision, HOLD)

    def test_nonfinite_or_boolean_limits_hold(self):
        for value in (float("nan"), float("inf"), -1, True):
            with self.subTest(value=str(value)):
                request = good_request("limit")
                request["requested_limits"]["speed"] = value
                self.assertEqual(Supervisor(clock=lambda: NOW).evaluate(request).decision, HOLD)

    def test_bad_consent_limits_hold(self):
        for value in (float("nan"), float("inf"), -1, True):
            with self.subTest(value=str(value)):
                request = good_request("consent-limit")
                request["consent"]["limits"]["speed"] = value
                self.assertEqual(Supervisor(clock=lambda: NOW).evaluate(request).decision, HOLD)

    def test_invalid_heartbeats_hold(self):
        for heartbeat in (float("nan"), float("inf"), True, "1000"):
            with self.subTest(value=str(heartbeat)):
                request = good_request("bad-heartbeat")
                request["heartbeats"] = [heartbeat]
                self.assertEqual(Supervisor(clock=lambda: NOW).evaluate(request).decision, HOLD)

    def test_invalid_clock_holds(self):
        for clock_value in (float("nan"), float("inf"), "1000"):
            result = Supervisor(clock=lambda: clock_value).evaluate(good_request("clock"))
            self.assertEqual(result.decision, HOLD)

    def test_empty_or_nonstring_request_id_holds(self):
        for rid in ("", "  ", None, 7):
            result = Supervisor(clock=lambda: NOW).evaluate(good_request(rid))
            self.assertEqual(result.decision, HOLD)

    def test_original_happy_path_still_review_only(self):
        result = Supervisor(clock=lambda: NOW).evaluate(good_request("valid"))
        self.assertEqual(result.decision, HUMAN_REVIEW)
        self.assertFalse(result.approval_granted)

    def test_recovery_requires_nonempty_new_id(self):
        s = Supervisor(clock=lambda: NOW)
        request = good_request("original")
        request["faults"] = ["injected"]
        held = s.evaluate(request)
        for bad_id in ("", None, 42):
            self.assertEqual(s.recover(held, good_request(bad_id)).decision, HOLD)


if __name__ == "__main__":
    unittest.main()
