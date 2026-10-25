"""999000 AUDIT - a local hash chain (offline, no hardware).

AuditChain() is in memory; AuditChain(path) opts into durable SQLite storage.
Stored chains are verified on load and before each transactional append. A stale
writer must reload instead of overwriting another writer's work. Storage errors
raise AuditError; callers must HOLD rather than treating them as a valid audit.

Hashes detect changes within a chain, not its authenticity. SQLite storage keeps
a count/head anchor, so deleting tail rows alone is detected on load. Deleting
rows AND editing the anchor, or rewriting all hashes, is still undetectable
without an independently retained expected_head. SQLite durability is local to one database;
this is neither a signed audit nor a cross-device log.
"""
from contextlib import closing
import hashlib
import json
import os
import sqlite3

GATE = "999000 AUDIT"
GENESIS = "0" * 64


def _hash(entry):
    body = {k: entry[k] for k in ("index", "gate", "outcome", "detail", "prev")}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


class AuditError(RuntimeError):
    """The local audit cannot be read or durably extended."""


class AuditChain:
    def __init__(self, path=None, *, expected_head=None):
        try:
            self.path = os.fspath(path) if path is not None else None
        except TypeError as exc:
            raise AuditError("audit path must be a file path") from exc
        self.entries = []
        if self.path is not None:
            if self.path in ("", ":memory:", b"", b":memory:"):
                raise AuditError("persistent audit requires a file path")
            try:
                with closing(self._connect()) as conn, conn:
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("CREATE TABLE IF NOT EXISTS audit_entries "
                                 "(position INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
                    conn.execute("CREATE TABLE IF NOT EXISTS audit_anchor "
                                 "(id INTEGER PRIMARY KEY CHECK (id = 0), count INTEGER NOT NULL, "
                                 "head TEXT NOT NULL)")
                    self.entries = self._read(conn)
                    if not verify_chain(self.entries, expected_head):
                        raise AuditError("audit checkpoint does not match")
                    self._check_anchor(conn, self.entries)
            except (sqlite3.Error, OSError, ValueError) as exc:
                raise AuditError("audit storage unavailable") from exc
        elif not verify_chain(self.entries, expected_head):
            raise AuditError("audit checkpoint does not match")

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=1.0)
        try:
            conn.execute("PRAGMA synchronous = FULL")
        except sqlite3.Error:
            conn.close()
            raise
        return conn

    @staticmethod
    def _check_anchor(conn, entries):
        """Stored count/head anchor, updated in the same transaction as each
        append. Deleting tail rows without also editing the anchor is detected
        even without expected_head. A pre-anchor database is anchored on first
        open (trust on first use); expected_head remains the stronger check."""
        row = conn.execute("SELECT count, head FROM audit_anchor WHERE id = 0").fetchone()
        head = entries[-1]["hash"] if entries else GENESIS
        if row is None:
            conn.execute("INSERT INTO audit_anchor (id, count, head) VALUES (0, ?, ?)",
                         (len(entries), head))
        elif tuple(row) != (len(entries), head):
            raise AuditError("audit anchor mismatch: entries were deleted or replaced")

    @staticmethod
    def _read(conn):
        try:
            rows = conn.execute("SELECT position, payload FROM audit_entries ORDER BY position").fetchall()
            entries = [json.loads(payload) for _, payload in rows]
            if any(position != i for i, (position, _) in enumerate(rows)) or not verify_chain(entries):
                raise AuditError("audit chain is malformed or damaged")
            return entries
        except (ValueError, TypeError, RecursionError) as exc:
            raise AuditError("audit chain is malformed or damaged") from exc

    @property
    def head(self):
        return self.entries[-1]["hash"] if self.entries else GENESIS

    def append(self, gate, outcome, detail=""):
        entry = {"index": len(self.entries), "gate": str(gate), "outcome": str(outcome),
                 "detail": str(detail), "prev": self.head}
        entry["hash"] = _hash(entry)
        if self.path is not None:
            try:
                with closing(self._connect()) as conn, conn:
                    conn.execute("BEGIN IMMEDIATE")
                    current = self._read(conn)
                    if current != self.entries:
                        raise AuditError("audit changed; reload before appending")
                    self._check_anchor(conn, current)
                    conn.execute("INSERT INTO audit_entries (position, payload) VALUES (?, ?)",
                                 (entry["index"], json.dumps(entry, sort_keys=True)))
                    conn.execute("UPDATE audit_anchor SET count = ?, head = ? WHERE id = 0",
                                 (len(current) + 1, entry["hash"]))
            except (sqlite3.Error, OSError, ValueError) as exc:
                raise AuditError("audit append was not confirmed durable") from exc
        self.entries.append(entry)
        return entry["hash"]


def verify_chain(entries, expected_head=None):
    """Check internal consistency and, optionally, a separately held checkpoint.

Without expected_head a valid prefix (or empty chain) cannot reveal truncation.
"""
    try:
        prev = GENESIS
        for i, e in enumerate(entries):
            if (type(e["index"]) is not int or e["index"] != i
                    or any(not isinstance(e[k], str) for k in ("gate", "outcome", "detail", "prev", "hash"))
                    or e["prev"] != prev or e["hash"] != _hash(e)):
                return False
            prev = e["hash"]
        return expected_head is None or prev == expected_head
    except Exception:  # malformed entries fail closed
        return False
