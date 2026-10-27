"""SYNTH_SHAI WhatsApp prototype: receive, authenticate, HOLD, human review.

No automatic outbound messages, no model APIs, and no external side effects.
Python 3.11+, standard library only.
"""
import hashlib
import hmac
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_BYTES = 65536
SEEN_TTL_SECONDS = 24 * 3600      # Meta retries webhooks for up to ~1 day
SEEN_MAX_IDS = 10000


class SeenIds:
    """Bounded, TTL'd in-memory seen-set of WhatsApp message ids (thread-safe).
    Limit: in-memory only; a restart forgets ids (a durable store is future work)."""
    def __init__(self, ttl=SEEN_TTL_SECONDS, max_ids=SEEN_MAX_IDS, clock=time.monotonic):
        self.ttl, self.max_ids, self.clock = ttl, max_ids, clock
        self._ids = OrderedDict()
        self._lock = threading.Lock()

    def first_time(self, message_id) -> bool:
        """True if this id has not been seen within the TTL; records it."""
        now = self.clock()
        with self._lock:
            while self._ids and next(iter(self._ids.values())) <= now - self.ttl:
                self._ids.popitem(last=False)
            if message_id in self._ids:
                return False
            self._ids[message_id] = now
            while len(self._ids) > self.max_ids:
                self._ids.popitem(last=False)
            return True


DEFAULT_DEDUPE_DB = str(Path(__file__).resolve().parent.parent / '.shai_data' / 'whatsapp_seen_ids.sqlite')


class SqliteSeenIds:
    """Persistent seen-set (survives restart), same interface as SeenIds.
    Stores only sha256(message id) and first-seen time; 24h TTL and a row cap.
    Each call opens, commits and CLOSES its own connection (no ResourceWarnings);
    BEGIN IMMEDIATE makes check-and-insert atomic across threads/processes."""
    def __init__(self, path, ttl=SEEN_TTL_SECONDS, max_ids=SEEN_MAX_IDS, clock=time.time):
        self.path, self.ttl, self.max_ids, self.clock = str(path), ttl, max_ids, clock
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS seen (id_sha256 TEXT PRIMARY KEY, first_seen REAL NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS seen_time ON seen(first_seen)')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level=None)

    def first_time(self, message_id) -> bool:
        key = hashlib.sha256(str(message_id).encode()).hexdigest()
        now = self.clock()
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                db.execute('DELETE FROM seen WHERE first_seen <= ?', (now - self.ttl,))
                fresh = db.execute('INSERT OR IGNORE INTO seen VALUES (?, ?)', (key, now)).rowcount == 1
                db.execute('DELETE FROM seen WHERE id_sha256 IN (SELECT id_sha256 FROM seen '
                           'ORDER BY first_seen DESC LIMIT -1 OFFSET ?)', (self.max_ids,))
                db.execute('COMMIT')
            except BaseException:
                db.execute('ROLLBACK')
                raise
        return fresh

    def count(self) -> int:
        with closing(self._connect()) as db:
            return db.execute('SELECT COUNT(*) FROM seen').fetchone()[0]


SEEN = None   # created lazily from SHAI_DEDUPE_DB (tests may patch in a SeenIds())
_SEEN_LOCK = threading.Lock()


def get_seen():
    """Persistent store by default. The in-memory SeenIds is for tests only:
    silently falling back to memory would lose dedupe on restart, so a store
    error fails closed (HTTP 503, so Meta retries later) instead."""
    global SEEN
    with _SEEN_LOCK:
        if SEEN is None:
            SEEN = SqliteSeenIds(os.environ.get('SHAI_DEDUPE_DB', DEFAULT_DEDUPE_DB))
        return SEEN


def new_messages(rows: list, seen: SeenIds) -> tuple:
    """Split extracted rows into (new, duplicate_count). A row without a string id
    cannot be deduplicated; it is kept (it is a HOLD draft anyway, never sent)."""
    fresh, dupes = [], 0
    for row in rows:
        mid = row.get('id')
        if isinstance(mid, str) and mid and not seen.first_time(mid):
            dupes += 1
            continue
        fresh.append(row)
    return fresh, dupes


class RateLimiter:
    """Sliding-window limits: per sender (hashed wa_id) and global. In-memory.
    Over-limit messages are dropped (no HOLD) but the webhook still returns 200:
    Meta retries non-2xx responses, so a 429 would cause a retry storm."""
    def __init__(self, per_sender=10, global_limit=100, window=60.0, clock=time.monotonic, max_senders=10000):
        self.per_sender, self.global_limit, self.window = per_sender, global_limit, window
        self.clock, self.max_senders = clock, max_senders
        self._senders = OrderedDict()
        self._global = []
        self._lock = threading.Lock()

    def allow(self, sender_key) -> bool:
        now = self.clock()
        cutoff = now - self.window
        with self._lock:
            self._global = [t for t in self._global if t > cutoff]
            if len(self._global) >= self.global_limit:
                return False
            key = sender_key or 'unknown-sender'
            hits = [t for t in self._senders.pop(key, []) if t > cutoff]
            if len(hits) >= self.per_sender:
                self._senders[key] = hits
                return False
            hits.append(now)
            self._senders[key] = hits
            while len(self._senders) > self.max_senders:
                self._senders.popitem(last=False)
            self._global.append(now)
            return True


def _env_int(name, default):
    try:
        value = int(os.environ.get(name, default))
        return value if value > 0 else default
    except ValueError:
        return default


LIMITER = None


def get_limiter():
    global LIMITER
    with _SEEN_LOCK:
        if LIMITER is None:
            LIMITER = RateLimiter(per_sender=_env_int('SHAI_RATE_PER_SENDER', 10),
                                  global_limit=_env_int('SHAI_RATE_GLOBAL', 100),
                                  window=float(_env_int('SHAI_RATE_WINDOW_SECONDS', 60)))
        return LIMITER


def apply_rate_limit(rows: list, limiter: RateLimiter) -> tuple:
    kept, dropped = [], 0
    for row in rows:
        if limiter.allow(row.get('sender_sha256')):
            kept.append(row)
        else:
            dropped += 1
    return kept, dropped


def verify_token_ok(expected: str, mode, provided) -> bool:
    """Constant-time hub.verify_token check."""
    if not expected or mode != ['subscribe'] or not isinstance(provided, list) or len(provided) != 1:
        return False
    return hmac.compare_digest(provided[0].encode(), expected.encode())

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
                    sender = message.get('from')
                    result.append({'id':message.get('id'),
                                   # only a hash of the sender is kept, for rate limiting
                                   'sender_sha256': hashlib.sha256(sender.encode()).hexdigest()
                                   if isinstance(sender, str) and sender else None,
                                   'decision':decide(message['text']['body'])})
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
        ok = verify_token_ok(token, params.get('hub.mode'), params.get('hub.verify_token'))
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
        # Replay/duplicate protection: a retried message id gets 200 but no second HOLD.
        try:
            decisions, duplicates = new_messages(decisions, get_seen())
        except (sqlite3.Error, OSError):
            print(json.dumps({'event':'dedupe_store_unavailable'}), flush=True)
            return self.respond(503, 'temporarily unavailable')
        # Dedupe first (a retry is not a new message), then rate-limit new messages.
        decisions, rate_limited = apply_rate_limit(decisions, get_limiter())
        # Deliberately log only decision type and count: no phone numbers or message bodies.
        print(json.dumps({'event':'authenticated_webhook','text_messages':len(decisions),
                          'duplicates_ignored':duplicates, 'rate_limited':rate_limited,
                          'states':[m['decision']['state'] for m in decisions]}), flush=True)
        return self.respond(200, 'accepted for review; no response sent')

if __name__ == '__main__':
    if not os.environ.get('SHAI_VERIFY_TOKEN') or not os.environ.get('SHAI_META_APP_SECRET'):
        raise SystemExit('Set SHAI_VERIFY_TOKEN and SHAI_META_APP_SECRET before starting.')
    host = os.environ.get('SHAI_HOST','127.0.0.1')
    port = int(os.environ.get('PORT','8080'))
    print(f'SHAI inbound-only prototype listening on {host}:{port}')
    ThreadingHTTPServer((host, port), Handler).serve_forever()
