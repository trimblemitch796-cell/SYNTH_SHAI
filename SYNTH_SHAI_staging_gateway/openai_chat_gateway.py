"""SYNTH_SHAI staging-only single-turn chat gateway.

No SHAI tool dispatch, shell execution, file access, or autonomous actions.
The API credential is never accepted from an HTTP client.
Not approved for public/mobile deployment; see README_STAGING.md.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import math
import os
import re
import threading
import time
from urllib import request

MAX_BODY_BYTES = 4096
MAX_MESSAGE_CHARS = 2000
MAX_REQUESTS_PER_MINUTE = 5
MAX_PILOT_SECONDS = 7 * 24 * 60 * 60
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
MODEL = "gpt-4.1-mini"
SYSTEM_PROMPT = (
    "You are SYNTH_SHAI in a staging-only, chat-only prototype. "
    "Provide helpful text responses. You have no tools and cannot take external actions. "
    "Never claim an action, deployment, or security verification took place. "
    "Keep consequential actions at 144 HOLD and refer them to human review."
)

class InvalidResponse(Exception):
    """The upstream response was malformed or contained no output text."""

def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj

def _extract_text(payload: dict) -> str:
    chunks = []
    for item in payload.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for block in item.get("content", []):
            if isinstance(block, dict) and block.get("type") == "output_text":
                text = block.get("text")
                if isinstance(text, str):
                    chunks.append(text)
    if not chunks:
        raise InvalidResponse()
    return "".join(chunks)[:4000]

def call_openai(api_key: str, message: str) -> str:
    """Use a fixed HTTPS destination; client cannot supply tools or parameters."""
    body = json.dumps({
        "model": MODEL,
        "instructions": SYSTEM_PROMPT,
        "input": message,
        "max_output_tokens": 256,
        "store": False,
    }).encode("utf-8")
    req = request.Request(
        OPENAI_ENDPOINT,
        data=body,
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=12) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise InvalidResponse()
    return _extract_text(payload)

def pilot_window_open(*, now=None) -> bool:
    """Fail closed unless a trusted host configured an active <=7-day pilot.

    The date is an absolute UTC cutoff, so restarting a process does not extend
    the pilot. This gates requests, NOT Render billing or container lifetime.
    """
    if os.environ.get("SHAI_PILOT_ENABLED") != "1":
        return False
    stamp = os.environ.get("SHAI_PILOT_DEADLINE_UTC", "")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", stamp):
        return False
    try:
        deadline = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
        current = time.time() if now is None else now
        return (type(current) in (int, float) and math.isfinite(current)
                and 0 < deadline - current <= MAX_PILOT_SECONDS)
    except (ValueError, OverflowError, OSError):
        return False


class SlidingWindowLimiter:
    """Single-process limiter, not a multi-instance security boundary."""
    def __init__(self, *, limit=MAX_REQUESTS_PER_MINUTE, window_seconds=60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._timestamps = deque()
        self._lock = threading.Lock()
    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._timestamps and now - self._timestamps[0] >= self.window_seconds:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.limit:
                return False
            self._timestamps.append(now)
            return True

def make_handler(*, send_to_openai=call_openai, limiter=None):
    limiter = limiter or SlidingWindowLimiter()

    class GatewayHandler(BaseHTTPRequestHandler):
        server_version = "SHAIStaging"
        sys_version = ""

        def log_message(self, format, *args):
            # Avoid logging messages, auth headers or provider response bodies.
            return

        def _reply(self, status, body):
            content = json.dumps(body, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if self.path == "/healthz":
                if not pilot_window_open():
                    self._reply(503, {"status": "144 HOLD"})
                    return
                self._reply(200, {"status": "staging"})
            else:
                self._reply(404, {"error": "not_found"})

        def do_POST(self):
            if self.path != "/chat":
                self._reply(404, {"error": "not_found"})
                return
            if not pilot_window_open():
                self._reply(503, {"error": "pilot_closed"})
                return
            expected = os.getenv("SHAI_GATEWAY_TOKEN", "")
            provided = self.headers.get("Authorization", "")
            if (len(expected) < 32 or not provided.startswith("Bearer ")
                    or not hmac.compare_digest(provided[7:], expected)):
                self._reply(401, {"error": "unauthorized"})
                return
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                self._reply(503, {"error": "not_configured"})
                return
            length_string = self.headers.get("Content-Length", "")
            if (self.headers.get("Transfer-Encoding")
                    or not re.fullmatch(r"[0-9]{1,5}", length_string)):
                self._reply(400, {"error": "invalid_length"})
                return
            length = int(length_string)
            if length == 0 or length > MAX_BODY_BYTES:
                self._reply(413, {"error": "invalid_size"})
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self._reply(415, {"error": "json_required"})
                return
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
            except (UnicodeError, ValueError):
                self._reply(400, {"error": "invalid_json"})
                return
            if not isinstance(data, dict) or set(data) != {"message"}:
                self._reply(400, {"error": "message_only"})
                return
            message = data["message"]
            if not isinstance(message, str) or not 1 <= len(message.strip()) <= MAX_MESSAGE_CHARS:
                self._reply(400, {"error": "invalid_message"})
                return
            if not limiter.allow():
                self._reply(429, {"error": "rate_limited"})
                return
            try:
                output = send_to_openai(api_key, message)
                if not isinstance(output, str) or not output:
                    raise InvalidResponse()
            except Exception:
                self._reply(502, {"error": "upstream_unavailable"})
                return
            self._reply(200, {"reply": output})
    return GatewayHandler

def main():
    if not os.getenv("OPENAI_API_KEY") or len(os.getenv("SHAI_GATEWAY_TOKEN", "")) < 32:
        raise SystemExit("Missing server-side API key or gateway token; refusing to start")
    if not pilot_window_open():
        raise SystemExit("144 HOLD: pilot disabled, expired, or invalid; refusing to start")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler())
    server.serve_forever()

if __name__ == "__main__":
    main()
