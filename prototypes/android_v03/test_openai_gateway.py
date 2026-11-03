"""Offline tests: no OpenAI API requests."""
import importlib.util
import io
import json
import pathlib
import unittest

PATH = pathlib.Path(__file__).with_name("openai_gateway.py")
spec = importlib.util.spec_from_file_location("shai_gateway", PATH)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class GatewayTests(unittest.TestCase):
    def test_no_key_fails_closed(self):
        with self.assertRaises(RuntimeError):
            gateway.reply("hello", "")

    def test_blank_message_rejected(self):
        with self.assertRaises(ValueError):
            gateway.reply(" ", "test")

    def test_overlong_message_rejected(self):
        with self.assertRaises(ValueError):
            gateway.reply("a" * 4001, "test")

    def test_request_has_no_tools_or_storage(self):
        captured = {}
        class FakeResponse:
            def __enter__(self):
                return io.BytesIO(json.dumps({"output": [{"type": "message", "content": [{"type": "output_text", "text": "Hello!"}]}]}).encode())
            def __exit__(self, *args):
                return False
        def fake_open(req, timeout):
            captured.update(json.loads(req.data))
            self.assertEqual(timeout, 20)
            return FakeResponse()
        self.assertEqual(gateway.reply("hello", "test", fake_open), "Hello!")
        self.assertEqual(captured["tools"], [])
        self.assertIs(captured["store"], False)
        self.assertIn("144 HOLD", captured["instructions"])
        self.assertEqual(captured["max_output_tokens"], 300)


if __name__ == "__main__":
    unittest.main()
