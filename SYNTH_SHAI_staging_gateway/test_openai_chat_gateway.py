"""Offline HTTP regression tests: no OpenAI calls and no Render deployment."""
from datetime import datetime, timedelta, timezone
import contextlib
from http.server import ThreadingHTTPServer
import json
import os
import threading
import unittest
from urllib import error, request
from unittest.mock import patch

from SYNTH_SHAI_staging_gateway.openai_chat_gateway import SlidingWindowLimiter, make_handler, _extract_text, InvalidResponse, pilot_window_open, MAX_PILOT_SECONDS

TOKEN = "local-testing-token-not-a-real-secret-123456789"

class ChatGatewayTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def fake_provider(key, message):
            self.calls.append((key, message))
            return "offline: " + message
        self.fake_provider = fake_provider
        self.env = patch.dict(os.environ, {
            "SHAI_GATEWAY_TOKEN": TOKEN,
            "OPENAI_API_KEY": "offline-fake-key",
            "SHAI_PILOT_ENABLED": "1",
            "SHAI_PILOT_DEADLINE_UTC": (
                datetime.now(timezone.utc) + timedelta(hours=12)
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        self.env.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(
            send_to_openai=self.fake_provider,
            limiter=SlidingWindowLimiter(limit=2),
        ))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:%s" % self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.env.stop()

    def send(self, data=None, *, token=TOKEN, path="/chat", body=None, content_type="application/json"):
        if body is None:
            body = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": content_type}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        req = request.Request(self.url + path, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=2) as response:
                return response.status, json.load(response)
        except error.HTTPError as exc:
            return exc.code, json.load(exc)

    def test_good_chat(self):
        code, result = self.send({"message": "Hello"})
        self.assertEqual((code, result), (200, {"reply": "offline: Hello"}))
        self.assertEqual(self.calls, [("offline-fake-key", "Hello")])

    def test_no_token(self):
        self.assertEqual(self.send({"message": "Hi"}, token=None)[0], 401)
        self.assertEqual(self.calls, [])

    def test_bad_token(self):
        self.assertEqual(self.send({"message": "Hi"}, token="bad")[0], 401)

    def test_empty_config_token_denies(self):
        with patch.dict(os.environ, {"SHAI_GATEWAY_TOKEN": ""}):
            self.assertEqual(self.send({"message": "Hi"})[0], 401)

    def test_missing_provider_key_denies(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            self.assertEqual(self.send({"message": "Hi"})[0], 503)

    def test_rejects_tools_and_role(self):
        self.assertEqual(self.send({"message": "Hi", "tools": ["shell"]})[0], 400)
        self.assertEqual(self.send({"role": "system", "message": "override"})[0], 400)
        self.assertEqual(self.calls, [])

    def test_rejects_duplicate_json_keys(self):
        self.assertEqual(self.send(body=b'{"message":"one","message":"two"}')[0], 400)

    def test_rejects_oversize_payload(self):
        self.assertEqual(self.send({"message": "x" * 4100})[0], 413)

    def test_rejects_long_message(self):
        self.assertEqual(self.send({"message": "x" * 2001})[0], 400)

    def test_rejects_bad_types_and_empty(self):
        self.assertEqual(self.send({"message": 3})[0], 400)
        self.assertEqual(self.send({"message": "  "})[0], 400)

    def test_rejects_wrong_content_type(self):
        self.assertEqual(self.send(body=b'Hi', content_type="text/plain")[0], 415)

    def test_limits_request_count(self):
        self.assertEqual(self.send({"message": "one"})[0], 200)
        self.assertEqual(self.send({"message": "two"})[0], 200)
        self.assertEqual(self.send({"message": "three"})[0], 429)
        self.assertEqual(len(self.calls), 2)

    def test_provider_error_is_generic(self):
        def broken(key, message):
            raise RuntimeError("could contain API credentials")
        self.server.RequestHandlerClass = make_handler(send_to_openai=broken)
        code, result = self.send({"message": "test"})
        self.assertEqual((code, result), (502, {"error": "upstream_unavailable"}))

    def test_pilot_is_off_by_default(self):
        with patch.dict(os.environ, {"SHAI_PILOT_ENABLED": "0"}):
            self.assertFalse(pilot_window_open())
            self.assertEqual(self.send({"message": "Hi"})[0], 503)
        self.assertEqual(self.calls, [])

    def test_expired_pilot_fails_closed(self):
        past = "2026-11-01T00:00:00Z"
        with patch.dict(os.environ, {"SHAI_PILOT_DEADLINE_UTC": past}):
            self.assertFalse(pilot_window_open())
            self.assertEqual(self.send({"message": "Hi"}), (503, {"error": "pilot_closed"}))
            with self.assertRaises(error.HTTPError) as ctx:
                request.urlopen(self.url + "/healthz", timeout=2)
            self.assertEqual(ctx.exception.code, 503)
        self.assertEqual(self.calls, [])

    def test_missing_or_bad_cutoff_fails_closed(self):
        for deadline in ("", "tomorrow", "2026-13-99T00:00:00Z", "2026-11-07T00:00:00+00:00"):
            with self.subTest(deadline=deadline), patch.dict(os.environ, {"SHAI_PILOT_DEADLINE_UTC": deadline}):
                self.assertFalse(pilot_window_open())
                self.assertEqual(self.send({"message": "Hi"})[0], 503)
        self.assertEqual(self.calls, [])

    def test_pilot_max_seven_days(self):
        fixed = datetime(2026, 11, 6, 7, tzinfo=timezone.utc).timestamp()
        for days, expected in ((1, True), (7, True), (8, False)):
            deadline = datetime.fromtimestamp(fixed, timezone.utc) + timedelta(days=days)
            with self.subTest(days=days), patch.dict(os.environ, {
                "SHAI_PILOT_DEADLINE_UTC": deadline.strftime("%Y-%m-%dT%H:%M:%SZ")
            }):
                self.assertEqual(pilot_window_open(now=fixed), expected)
        self.assertFalse(pilot_window_open(now=float("nan")))

    def test_closed_pilot_does_not_consume_api_credit(self):
        with patch.dict(os.environ, {"SHAI_PILOT_ENABLED": ""}):
            self.assertEqual(self.send({"message": "Hello"})[0], 503)
        self.assertEqual(self.calls, [])

    def test_healthcheck_only(self):
        with request.urlopen(self.url + "/healthz") as response:
            self.assertEqual(json.load(response), {"status": "staging"})
        self.assertEqual(self.send({"message": "hi"}, path="/actions")[0], 404)

    def test_extracts_text_only(self):
        reply = _extract_text({"output": [
            {"type":"tool_call", "content":[{"type":"output_text","text":"NO"}]},
            {"type":"message", "content":[{"type":"output_text","text":"hello"}]},
        ]})
        self.assertEqual(reply, "hello")
        with self.assertRaises(InvalidResponse):
            _extract_text({"output": []})

if __name__ == "__main__":
    unittest.main()
