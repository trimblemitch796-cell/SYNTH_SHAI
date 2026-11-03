"""SYNTH_SHAI V0.3: local-only OpenAI conversation gateway prototype.

Research code. Do not expose to a public network or deploy.
No AI tools, execution capabilities, or outbound messaging.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODEL = os.environ.get("SHAI_MODEL", "gpt-6-luna")
MAX_BYTES = 8192
MAX_OUTPUT_TOKENS = 300
SYSTEM = (
    "You are SYNTH_SHAI, a conversational research prototype. "
    "Answer naturally, admit uncertainty, and never claim to have performed actions. "
    "You have no tools, no authority to execute commands, and no access to accounts. "
    "144 HOLD applies to consequential actions. The user retains final authority."
)


def reply(message, api_key, opener=urlopen):
    if not isinstance(message, str) or not message.strip() or len(message) > 4000:
        raise ValueError("invalid message")
    if not api_key:
        raise RuntimeError("API key not configured")
    payload = {
        "model": MODEL,
        "instructions": SYSTEM,
        "input": message,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
        "tools": [],
    }
    req = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with opener(req, timeout=20) as response:
        result = json.load(response)
    text = []
    for item in result.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                text.append(part.get("text", ""))
    return "\n".join(text).strip() or "No text response returned."


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/v1/chat":
            self.send_error(404)
            return
        # This loopback-only development server is intentionally NOT a
        # production authenticated gateway.
        length = self.headers.get("Content-Length", "")
        if not length.isdigit() or int(length) > MAX_BYTES:
            self.send_error(413)
            return
        try:
            data = json.loads(self.rfile.read(int(length)))
            answer = reply(data.get("message"), os.environ.get("OPENAI_API_KEY"))
            status, result = 200, {"reply": answer}
        except (ValueError, KeyError, json.JSONDecodeError):
            status, result = 400, {"error": "Invalid request"}
        except (HTTPError, URLError, RuntimeError, TimeoutError):
            status, result = 503, {"error": "Model unavailable"}
        raw = json.dumps(result).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


if __name__ == "__main__":
    # Loopback only. No public binding, no remote Android access.
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
