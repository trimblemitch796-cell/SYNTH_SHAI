"""SYNTH_SHAI V2: offline Ed25519-authenticated operator revocation.

Research-only, no network endpoints, no runtime execution authority.
Administrator trust anchors and the SQLite location come from the trusted host.
"""
import math
import sqlite3
from contextlib import closing

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from offline_approval_v1 import HOLD, _database, _identifier, _initialize, canonical

REVOKED = "REVOKED_NO_EXECUTION"
DOMAIN = b"SHAI-ADMIN-REVOKE-V2\\x00".replace(b"\\x00", b"\x00")
FIELDS = frozenset(("operation", "admin_id", "operator_id", "nonce", "expires_at", "signature"))
SIGNED = ("operation", "admin_id", "operator_id", "nonce", "expires_at")


def _check(payload, now, pinned_admin_keys):
    if type(payload) is not dict or payload.keys() != FIELDS:
        return False
    if payload["operation"] != "revoke_operator":
        return False
    if not all(_identifier(payload[k]) for k in ("admin_id", "operator_id", "nonce")):
        return False
    if len(payload["nonce"]) < 16 or len(payload["nonce"]) > 128:
        return False
    expiry = payload["expires_at"]
    if type(expiry) not in (float, int) or not math.isfinite(expiry):
        return False
    if type(now) not in (float, int) or not math.isfinite(now):
        return False
    if not now < expiry <= now + 300:
        return False
    if type(payload["signature"]) is not str or len(payload["signature"]) != 128:
        return False
    if type(pinned_admin_keys) is not dict:
        return False
    public = pinned_admin_keys.get(payload["admin_id"])
    if type(public) is not bytes or len(public) != 32:
        return False
    signature = bytes.fromhex(payload["signature"])
    signed = {key: payload[key] for key in SIGNED}
    Ed25519PublicKey.from_public_bytes(public).verify(signature, DOMAIN + canonical(signed))
    return True


def authenticated_revoke(payload, *, pinned_admin_keys, trusted_database_path, now):
    """Verify and atomically record a signed administrator revocation.

    Returns REVOKED_NO_EXECUTION only after a durable local transaction.
    Failed requests return HOLD and never consume a nonce.
    """
    try:
        if not _check(payload, now, pinned_admin_keys):
            return HOLD
        with closing(_database(trusted_database_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                _initialize(conn)
                conn.execute("CREATE TABLE IF NOT EXISTS admin_revocation_nonces (nonce TEXT PRIMARY KEY)")
                conn.execute("INSERT INTO admin_revocation_nonces(nonce) VALUES (?)", (payload["nonce"],))
                conn.execute("INSERT OR IGNORE INTO revoked(operator_id) VALUES (?)", (payload["operator_id"],))
                conn.commit()
                return REVOKED
            except sqlite3.Error:
                conn.rollback()
                return HOLD
    except (InvalidSignature, ValueError, TypeError, KeyError, UnicodeError,
            OverflowError, sqlite3.Error, OSError):
        return HOLD
