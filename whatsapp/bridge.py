"""SYNTH_SHAI WhatsApp prototype: receive, authenticate, HOLD, human review.

No automatic outbound messages, no model APIs, and no external side effects.
Python 3.11+, standard library only.
"""
import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_BYTES = 65536

def verify_signature(secret: str, raw: bytes, header: str) -> bool:
    if not secret or not header.startswith('sha256='):
        return False
    provided = header[7:]
    if len(provided) != 64:
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided, expected)

def decide(text: str) -> dict:
    """Return advisory, non-actionable decision record; never authorizes messaging."""
    normalized = text.strip()
    if not normalized:
        return {'state':'144 HOLD', 'reason':'Empty message', 'reply_draft':None}
    if normalized.lower() in ('/status', 'status'):
        draft = 'SHAI Bridge V1: inbound prototype only. Human review is required. No AI models are connected.'
    elif normalized.lower().startswith('/compare'):
        draft = 'Comparison requested. ChatGPT, Gemini, Claude and Grok integrations are not connected or verified. 144 HOLD.'
    elif normalized.lower().startswith('shai'):
        draft = 'SHAI received your message. A human must review and approve any reply.'
    else:
        draft = 'Message received for human review. No automated response has been sent.'
    return {'state':'144 HOLD', 'reason':'Human review required; outbound disabled', 'reply_draft':draft}

def extract_messages(payload: dict) -> list:
    result = []
    if payload.get('object') != 'whatsapp_business_account':
        return result
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') != 'messages':
                continue
            for message in change.get('value', {}).get('messages', []):
                if message.get('type') == 'text' and isinstance(message.get('text', {}).get('body'), str):
                    result.append({'id':message.get('id'), 'decision':decide(message['text']['body'])})
    return result

class Handler(BaseHTTPRequestHandler):
    def respond(self, code: int, data: str):
        body = data.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == '/health':
            return self.respond(200, 'ready: inbound only; outbound disabled')
        if url.path != '/webhook':
            return self.respond(404, 'not found')
        params = parse_qs(url.query)
        token = os.environ.get('SHAI_VERIFY_TOKEN','')
        ok = (bool(token) and params.get('hub.mode') == ['subscribe']
              and params.get('hub.verify_token') == [token])
        return self.respond(200 if ok else 403, params.get('hub.challenge',[''])[0] if ok else 'forbidden')

    def do_POST(self):
        if urlsplit(self.path).path != '/webhook':
            return self.respond(404, 'not found')
        try:
            n = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.respond(400, 'bad length')
        if n <= 0 or n > MAX_BYTES:
            return self.respond(413, 'invalid size')
        raw = self.rfile.read(n)
        secret = os.environ.get('SHAI_META_APP_SECRET','')
        if not verify_signature(secret, raw, self.headers.get('X-Hub-Signature-256','')):
            return self.respond(401, 'invalid signature')
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError('not object')
            decisions = extract_messages(payload)
        except (ValueError, TypeError, AttributeError):
            return self.respond(400, 'invalid payload')
        # Deliberately log only decision type and count: no phone numbers or message bodies.
        print(json.dumps({'event':'authenticated_webhook','text_messages':len(decisions),
                          'states':[m['decision']['state'] for m in decisions]}), flush=True)
        return self.respond(200, 'accepted for review; no response sent')

if __name__ == '__main__':
    if not os.environ.get('SHAI_VERIFY_TOKEN') or not os.environ.get('SHAI_META_APP_SECRET'):
        raise SystemExit('Set SHAI_VERIFY_TOKEN and SHAI_META_APP_SECRET before starting.')
    host = os.environ.get('SHAI_HOST','127.0.0.1')
    port = int(os.environ.get('PORT','8080'))
    print(f'SHAI inbound-only prototype listening on {host}:{port}')
    ThreadingHTTPServer((host, port), Handler).serve_forever()
