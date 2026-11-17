"""SYNTH_SHAI 144 HOLD review queue (offline, stdlib only).

Every inbound WhatsApp text that passes signature, dedupe and rate-limit checks is
stored here as a PENDING 144 HOLD item. A human reviewer can list items, view one,
and record APPROVE or REJECT with a reason.

Approval records a human decision ONLY. Nothing is ever sent: the approved state is
named APPROVED_NOT_SENT, and this module has no network or outbound code at all.

Data handling: the DB holds message text, which a human must read to review, so it
is SENSITIVE. It lives under the gitignored `.shai_data/` by default (SHAI_REVIEW_DB
overrides). The sender's number is never stored, only its SHA-256 (as the rate
limiter does); the WhatsApp message id is also stored as a SHA-256.

Decisions are append-only: one decision per item (UNIQUE), SQLite triggers refuse
UPDATE/DELETE on the decisions table, and each decision is hash-chained
(prev_hash -> hash) so edits are detectable with verify_decisions(). Like the
existing audit, a DB owner can still rewrite the whole file; keep the head hash
externally for stronger evidence.
"""
import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

PENDING = 'PENDING_REVIEW'
APPROVED = 'APPROVED_NOT_SENT'   # human approved the draft; NOTHING was sent
REJECTED = 'REJECTED'
DECISIONS = {'approve': APPROVED, 'reject': REJECTED}
GENESIS = '0' * 64

MAX_BODY = 4096
MAX_REASON = 500
REVIEWER_RE = re.compile(r'^[A-Za-z0-9._-]{1,64}$')
ITEM_RE = re.compile(r'^HOLD-[0-9a-f]{32}$')

DEFAULT_REVIEW_DB = str(Path(__file__).resolve().parent.parent / '.shai_data' / 'whatsapp_review.sqlite')

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  item_id TEXT PRIMARY KEY,
  message_id_sha256 TEXT UNIQUE NOT NULL,
  sender_sha256 TEXT,
  body TEXT NOT NULL,
  reply_draft TEXT,
  hold_reason TEXT NOT NULL,
  received_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id TEXT UNIQUE NOT NULL REFERENCES items(item_id),
  decision TEXT NOT NULL CHECK (decision IN ('APPROVED_NOT_SENT', 'REJECTED')),
  reviewer TEXT NOT NULL,
  reason TEXT NOT NULL,
  decided_at REAL NOT NULL,
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS decisions_no_update BEFORE UPDATE ON decisions
  BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS decisions_no_delete BEFORE DELETE ON decisions
  BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS items_no_delete BEFORE DELETE ON items
  BEGIN SELECT RAISE(ABORT, 'held items are kept for audit'); END;
"""


class ReviewError(ValueError):
    """Invalid input or a refused decision. `code` is a short machine reason."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _decision_hash(prev_hash, record):
    data = json.dumps([prev_hash, record], sort_keys=True, separators=(',', ':'))
    return _sha(data)


class ReviewQueue:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = str(path), clock
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.executescript(_SCHEMA)

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level=None)

    # --- intake (called by the webhook) ---
    def enqueue(self, message_id, sender_sha256, body, reply_draft, hold_reason):
        """Store one held message. Idempotent by message id. Returns the item id."""
        if not isinstance(body, str):
            raise ReviewError('invalid_body')
        body = body[:MAX_BODY]
        mid = _sha(str(message_id)) if message_id else _sha('no-id:' + uuid.uuid4().hex)
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                row = db.execute('SELECT item_id FROM items WHERE message_id_sha256=?', (mid,)).fetchone()
                if row:
                    item_id = row[0]
                else:
                    item_id = 'HOLD-' + uuid.uuid4().hex
                    db.execute('INSERT INTO items VALUES (?,?,?,?,?,?,?)',
                               (item_id, mid, sender_sha256, body, reply_draft, hold_reason, self.clock()))
                db.execute('COMMIT')
            except BaseException:
                db.execute('ROLLBACK')
                raise
        return item_id

    # --- reading ---
    @staticmethod
    def _row_to_item(row):
        (item_id, sender, body, draft, hold_reason, received_at,
         decision, reviewer, reason, decided_at, dhash) = row
        item = {'item_id': item_id, 'sender_sha256': sender, 'body': body, 'reply_draft': draft,
                'hold_reason': hold_reason, 'received_at': received_at,
                'status': decision or PENDING, 'sent': False}
        if decision:
            item['decision'] = {'decision': decision, 'reviewer': reviewer, 'reason': reason,
                                'decided_at': decided_at, 'hash': dhash}
        return item

    _SELECT = ('SELECT i.item_id, i.sender_sha256, i.body, i.reply_draft, i.hold_reason, i.received_at, '
               'd.decision, d.reviewer, d.reason, d.decided_at, d.hash '
               'FROM items i LEFT JOIN decisions d ON d.item_id = i.item_id ')

    def list_items(self, status=PENDING, limit=100):
        limit = max(1, min(int(limit), 500))
        with closing(self._connect()) as db:
            if status == PENDING:
                rows = db.execute(self._SELECT + 'WHERE d.item_id IS NULL ORDER BY i.received_at LIMIT ?',
                                  (limit,)).fetchall()
            elif status in (APPROVED, REJECTED):
                rows = db.execute(self._SELECT + 'WHERE d.decision = ? ORDER BY i.received_at LIMIT ?',
                                  (status, limit)).fetchall()
            else:
                raise ReviewError('invalid_status')
        return [self._row_to_item(r) for r in rows]

    def get(self, item_id):
        if not isinstance(item_id, str) or not ITEM_RE.match(item_id):
            raise ReviewError('invalid_item_id')
        with closing(self._connect()) as db:
            row = db.execute(self._SELECT + 'WHERE i.item_id = ?', (item_id,)).fetchone()
        if row is None:
            raise ReviewError('not_found')
        return self._row_to_item(row)

    # --- deciding ---
    def decide(self, item_id, action, reviewer, reason):
        """Record one human decision. Re-sending the identical decision is idempotent
        (returns the stored record, `idempotent=True`); any different decision on an
        already-decided item is refused with `already_decided`."""
        if action not in DECISIONS:
            raise ReviewError('invalid_decision')
        if not isinstance(reviewer, str) or not REVIEWER_RE.match(reviewer):
            raise ReviewError('invalid_reviewer')
        if not isinstance(reason, str) or not reason.strip() or len(reason) > MAX_REASON:
            raise ReviewError('reason_required')
        if not isinstance(item_id, str) or not ITEM_RE.match(item_id):
            raise ReviewError('invalid_item_id')
        decision, reason = DECISIONS[action], reason.strip()
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                if db.execute('SELECT 1 FROM items WHERE item_id=?', (item_id,)).fetchone() is None:
                    raise ReviewError('not_found')
                prior = db.execute('SELECT decision, reviewer, reason, decided_at, hash FROM decisions '
                                   'WHERE item_id=?', (item_id,)).fetchone()
                if prior:
                    db.execute('ROLLBACK')
                    if prior[:3] == (decision, reviewer, reason):
                        return {'item_id': item_id, 'decision': prior[0], 'reviewer': prior[1],
                                'reason': prior[2], 'decided_at': prior[3], 'hash': prior[4],
                                'idempotent': True, 'sent': False}
                    raise ReviewError('already_decided')
                last = db.execute('SELECT hash FROM decisions ORDER BY seq DESC LIMIT 1').fetchone()
                prev = last[0] if last else GENESIS
                record = {'item_id': item_id, 'decision': decision, 'reviewer': reviewer,
                          'reason': reason, 'decided_at': self.clock()}
                h = _decision_hash(prev, record)
                db.execute('INSERT INTO decisions (item_id, decision, reviewer, reason, decided_at, '
                           'prev_hash, hash) VALUES (?,?,?,?,?,?,?)',
                           (item_id, decision, reviewer, reason, record['decided_at'], prev, h))
                db.execute('COMMIT')
            except ReviewError:
                if db.in_transaction:
                    db.execute('ROLLBACK')
                raise
            except BaseException:
                if db.in_transaction:
                    db.execute('ROLLBACK')
                raise
        return dict(record, hash=h, idempotent=False, sent=False)

    def audit_trail(self):
        with closing(self._connect()) as db:
            rows = db.execute('SELECT seq, item_id, decision, reviewer, reason, decided_at, prev_hash, hash '
                              'FROM decisions ORDER BY seq').fetchall()
        keys = ('seq', 'item_id', 'decision', 'reviewer', 'reason', 'decided_at', 'prev_hash', 'hash')
        return [dict(zip(keys, r)) for r in rows]

    def verify_decisions(self, expected_head=None):
        prev = GENESIS
        for d in self.audit_trail():
            record = {k: d[k] for k in ('item_id', 'decision', 'reviewer', 'reason', 'decided_at')}
            if d['prev_hash'] != prev or d['hash'] != _decision_hash(prev, record):
                return False
            prev = d['hash']
        return expected_head is None or prev == expected_head
