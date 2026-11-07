"""USB/emulator lab only: real /chat handler, synthetic credentials and provider."""
import argparse
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
import os

from .openai_chat_gateway import make_handler
from .pilot_security import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["reply", "unauthorized", "limited", "closed"])
    mode = parser.parse_args().mode
    os.environ.update({
        "OPENAI_API_KEY": "unused-synthetic-fixture",
        "SHAI_PILOT_ENABLED": "0" if mode == "closed" else "1",
        "SHAI_PILOT_DEADLINE_UTC": (datetime.now(timezone.utc) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    def authenticate(marker):
        if mode != "unauthorized" and marker == "shai-loopback-fixture-only":
            return Session("fixture-user", "fixture-session")
        return None

    handler = make_handler(
        authenticate=authenticate,
        reserve=lambda _: "limited" if mode == "limited" else "accepted",
        send_to_openai=lambda _, message: "fixture received: " + message,
    )
    with ThreadingHTTPServer(("127.0.0.1", 18765), handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
