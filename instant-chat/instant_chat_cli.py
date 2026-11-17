"""Review-only terminal client for SYNTH_SHAI's existing /chat gateway.

This cannot activate the pilot, issue identities, or contact OpenAI directly.
144 HOLD applies; a reviewed HTTPS gateway and valid SHAI JWT are required.
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 4096
JWT = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


class ChatUnavailable(Exception):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request(message: str, session: str, origin: str) -> Request:
    parts = urlsplit(origin)
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.path not in ("", "/") or parts.query or parts.fragment):
        raise ChatUnavailable("A trusted HTTPS gateway origin is required.")
    if not isinstance(session, str) or len(session) > 4096 or not JWT.fullmatch(session):
        raise ChatUnavailable("An approved short-lived SHAI session JWT is required.")
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= 2000:
        raise ChatUnavailable("Message length must be between 1 and 2,000 characters.")
    body = json.dumps({"message": message.strip()}, ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_BYTES:
        raise ChatUnavailable("Message is too large.")
    return Request(origin.rstrip("/") + "/chat", data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + session,
        "Cache-Control": "no-store",
    })


def reply(message: str, session: str, origin: str, *, opener=None) -> str:
    request = _request(message, session, origin)
    http = opener or build_opener(HTTPSHandler(), _NoRedirect())
    try:
        with http.open(request, timeout=12) as response:
            raw = response.read(8193)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        # Never echo an upstream response body, session, or provider key.
        raise ChatUnavailable("Gateway rejected the request or is unavailable.") from None
    if len(raw) > 8192:
        raise ChatUnavailable("Gateway response exceeded the size limit.")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise ChatUnavailable("Gateway returned malformed JSON.") from None
    if (not isinstance(data, dict) or set(data) != {"reply"}
            or not isinstance(data["reply"], str) or not data["reply"].strip()
            or len(data["reply"]) > 4000):
        raise ChatUnavailable("Gateway returned an invalid reply.")
    return data["reply"]


def main() -> int:
    origin = os.getenv("SHAI_GATEWAY_ORIGIN", "")
    session = os.getenv("SHAI_SESSION_JWT", "")
    try:
        _request("preflight", session, origin)
    except ChatUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print("SYNTH_SHAI chat client / 144 HOLD / operator only / quit to exit")
    while True:
        try:
            line = input("You> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line.strip().lower() in ("quit", "exit"):
            return 0
        try:
            answer = reply(line, session, origin)
            print("SHAI prototype> " + ''.join(
                ch if ch.isprintable() or ch in "\n\t" else "�" for ch in answer
            ))
        except ChatUnavailable as exc:
            print("HOLD> " + str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
