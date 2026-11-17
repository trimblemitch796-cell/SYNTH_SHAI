"""No-network, fake-HTTP tests for review-only terminal client."""
import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import MagicMock
from instant_chat_cli import ChatUnavailable, _request, reply

JWT = "ab.cd.ef"
ORIGIN = "https://staging.example.org"


class _Response:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, limit):
        return self.payload[:limit]


class InstantChatCliTests(unittest.TestCase):
    def test_contract(self):
        req = _request(" Xin chào 🙏 ", JWT, ORIGIN)
        self.assertEqual(req.full_url, ORIGIN + "/chat")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data), {"message": "Xin chào 🙏"})
        self.assertEqual(req.get_header("Authorization"), "Bearer " + JWT)

    def test_refuses_http_and_auth_bypass(self):
        for origin in ("http://staging.example.org", "https://attacker@staging.example.org", "https://staging.example.org/evil", "https://staging.example.org?token=1"):
            with self.subTest(origin=origin), self.assertRaises(ChatUnavailable):
                _request("hi", JWT, origin)
        for token in ("", "not-a-session", "idtoken"):
            with self.subTest(token=token), self.assertRaises(ChatUnavailable):
                _request("hi", token, ORIGIN)

    def test_input_limits(self):
        for msg in ("", "  ", "x" * 2001, "\u0000" * 1800):
            with self.subTest(msg=msg[:10]), self.assertRaises(ChatUnavailable):
                _request(msg, JWT, ORIGIN)

    def test_success(self):
        fake = MagicMock()
        fake.open.return_value = _Response(b'{"reply":"Hello!"}')
        self.assertEqual(reply("Hi", JWT, ORIGIN, opener=fake), "Hello!")
        self.assertEqual(fake.open.call_args.kwargs["timeout"], 12)

    def test_errors_do_not_leak_upstream(self):
        fake = MagicMock()
        fake.open.side_effect = HTTPError(ORIGIN, 401, "secret key", None, io.BytesIO(b"private"))
        with self.assertRaises(ChatUnavailable) as err:
            reply("Hi", JWT, ORIGIN, opener=fake)
        self.assertNotIn("secret", str(err.exception))
        self.assertNotIn("private", str(err.exception))

    def test_malformed_response(self):
        for payload in (b"not json", b'{"reply":""}', b'{"reply":"hi","tool":1}', b"x" * 9000):
            fake = MagicMock()
            fake.open.return_value = _Response(payload)
            with self.subTest(payload=payload[:12]), self.assertRaises(ChatUnavailable):
                reply("Hi", JWT, ORIGIN, opener=fake)


if __name__ == "__main__":
    unittest.main()
