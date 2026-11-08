"""Offline expiry and suspension-request tests: never call the Render API."""
import unittest
from urllib.request import Request
from SYNTH_SHAI_staging_gateway import render_sunset


class FakeResponse:
    status = 202
    def __enter__(self): return self
    def __exit__(self, *args): return False


class RenderSunsetTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def fake_open(req, timeout):
            self.calls.append((req, timeout))
            return FakeResponse()
        self.fake_open = fake_open
        self.settings = dict(service_id="srv-abcdef1234567890",
                             token="test-token-not-a-real-render-api-key",
                             deadline_utc="2026-11-13T07:00:00Z",
                             opener=self.fake_open,
                             now=1794553201)

    def test_default_dry_run(self):
        self.assertEqual(render_sunset.suspend_if_due(**self.settings), "dry_run")
        self.assertEqual(self.calls, [])

    def test_cannot_run_before_deadline(self):
        self.settings["now"] = 1794553199
        self.assertEqual(render_sunset.suspend_if_due(**self.settings, execute=True, approved=True), "not_due")
        self.assertEqual(self.calls, [])

    def test_requires_both_flags(self):
        self.assertEqual(render_sunset.suspend_if_due(**self.settings, execute=True), "dry_run")
        self.assertEqual(render_sunset.suspend_if_due(**self.settings, approved=True), "dry_run")
        self.assertEqual(self.calls, [])

    def test_invalid_config_is_rejected(self):
        self.settings["service_id"] = "wrong"
        self.assertEqual(render_sunset.suspend_if_due(**self.settings, execute=True, approved=True), "invalid_configuration")
        self.assertEqual(self.calls, [])

    def test_builds_expected_api_request(self):
        self.assertEqual(render_sunset.suspend_if_due(**self.settings, execute=True, approved=True), "suspend_accepted")
        req, timeout = self.calls[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, "https://api.render.com/v1/services/srv-abcdef1234567890/suspend")
        self.assertEqual(timeout, 15)

    def test_deadline_parse_fail_closed(self):
        self.settings["deadline_utc"] = "tomorrow"
        self.assertEqual(render_sunset.suspend_if_due(**self.settings, execute=True, approved=True), "not_due")
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
