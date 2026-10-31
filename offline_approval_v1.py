"""Offline signed human-approval *validation*, without an execution capability.

This is a research prototype. Trusted operator keys, database path, and clock
must come from a separate trusted host. Never attach an actuator or network
execution endpoint to this module.
"""
import hashlib
import hmac
import json
import math
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

HOLD = "144 HOLD"
VALIDATED = "VALIDATED_NO_EXECUTION"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUEST_FIELDS = frozenset(("request_id", "action", "plan_sha256"))
APPROVAL_FIELDS = frozenset(("operator_id", "request_id", "action", "plan_sha256", "nonce", "expires_at", "signature"))
SIGNED_FIELDS = ("operator_id", "request_id", "action", "plan_sha256", "nonce", "expires_at")


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _identifier(value):
    return isinstance(value, str) and 1 <= len(value) <= 128 and value.strip() == value and bool(value)


def _valid_request(request):
    return (type(request) is dict and request.keys() == REQUEST_FIELDS
            and _identifier(request["request_id"])
            and _identifier(request["action"])
            and type(request["plan_sha256"]) is str
            and HEX64.fullmatch(request["plan_sha256"]) is not None)


def _valid_approval(approval):
    return (type(approval) is dict and approval.keys() == APPROVAL_FIELDS
            and all(_identifier(approval[k]) for k in ("operator_id", "request_id", "action", "nonce"))
            and len(approval["nonce"]) >= 16
            and type(approval["plan_sha256"]) is str
            and HEX64.fullmatch(approval["plan_sha256"]) is not None
            and type(approval["signature"]) is str
            and len(approval["signature"]) == 128
            and type(approval["expires_at"]) in (int, float)
            and math.isfinite(approval["expires_at"]))


def _database(db):
    # File path only, not in-memory, URI, or request-controlled storage.
    if not isinstance(db, str) or not db or db == ":memory:" or db.startswith("file:"):
        raise ValueError("trusted file-backed database required")
    if not Path(db).is_absolute():
        raise ValueError("absolute database path required")
    return sqlite3.connect(db, timeout=5, isolation_level=None)


def _initialize(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS consumed (nonce TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS revoked (operator_id TEXT PRIMARY KEY)")


def revoke_operator(operator_id, *, trusted_database_path):
    """Trusted offline administrator operation only; no caller authentication.

    The surrounding host MUST authenticate this call and protect its database.
    """
    if not _identifier(operator_id):
        return False
    try:
        with closing(_database(trusted_database_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                _initialize(conn)
                conn.execute("INSERT OR IGNORE INTO revoked(operator_id) VALUES (?)", (operator_id,))
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                return False
    except (OSError, sqlite3.Error, ValueError):
        return False


def validate_once(request, approval, *, trusted_operator_keys, trusted_database_path, now):
    """Fail closed. Success validates a one-use signature; NEVER executes actions.

    trusted_operator_keys maps operator ID to a 32-byte pinned Ed25519 public key.
    It must be supplied by the trusted host, never by the request.
    """
    try:
        if not _valid_request(request) or not _valid_approval(approval):
            return HOLD
        if type(now) not in (int, float) or not math.isfinite(now):
            return HOLD
        if not isinstance(trusted_operator_keys, dict):
            return HOLD
        if any(not hmac.compare_digest(request[k], approval[k]) for k in REQUEST_FIELDS):
            return HOLD
        if approval["expires_at"] <= now or approval["expires_at"] > now + 300:
            return HOLD
        pub = trusted_operator_keys.get(approval["operator_id"])
        if not isinstance(pub, bytes) or len(pub) != 32:
            return HOLD
        signature = bytes.fromhex(approval["signature"])
        payload = {field: approval[field] for field in SIGNED_FIELDS}
        Ed25519PublicKey.from_public_bytes(pub).verify(signature, canonical(payload))
        with closing(_database(trusted_database_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                _initialize(conn)
                if conn.execute("SELECT 1 FROM revoked WHERE operator_id=?", (approval["operator_id"],)).fetchone():
                    conn.rollback()
                    return HOLD
                conn.execute("INSERT INTO consumed(nonce) VALUES (?)", (approval["nonce"],))
                conn.commit()
            except Exception:
                conn.rollback()
                return HOLD
        return VALIDATED
    except (InvalidSignature, ValueError, TypeError, KeyError, OverflowError, UnicodeError, sqlite3.Error, OSError):
        return HOLD
