"""Offline research only: atomic, one-use, server-bound Google login challenges.

No network, HTTP route, public login, Google key fetch, session issuer or action.
An actual endpoint MUST supply a server-authenticated transaction binding, not
a browser/user-controlled value. Never put signing keys or a provider key here.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import math
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import quote

from .google_oidc_preflight import verify_google_id_token, VerifiedGoogleSubject

CHALLENGE_TTL_SECONDS = 300
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_BINDING_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class LoginChallenge:
    transaction_id: str
    nonce: str
    expires_at: float


def _trusted_db_path(path):
    if (type(path) is not str or not Path(path).is_absolute()
            or not Path(path).is_file()):
        raise ValueError("existing operator-provisioned absolute SQLite file required")
    return path


def _open_store(path):
    # mode=rw: a request must never silently create a replacement or new store.
    return sqlite3.connect("file:" + quote(_trusted_db_path(path)) + "?mode=rw",
                           uri=True, timeout=2, isolation_level=None)


def initialize_challenge_store(path):
    """Operator-only offline provisioning. NOT callable from HTTP requests."""
    if type(path) is not str or not Path(path).is_absolute():
        raise ValueError("operator-controlled absolute path required")
    if Path(path).is_symlink():
        raise ValueError("symlink store refused")
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS google_login_challenges ("
            "transaction_id TEXT PRIMARY KEY, nonce_hash TEXT NOT NULL, "
            "binding_hash TEXT NOT NULL, issued_at REAL NOT NULL, "
            "expires_at REAL NOT NULL)"
        )


def _clock(now):
    value = time.time() if now is None else now
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid clock")
    return float(value)


def issue_challenge(path, trusted_binding_hash, *, now=None):
    """Create one server-issued challenge for an independently bound client.

    trusted_binding_hash is SHA256 of a trusted server-managed session binding,
    NOT a hash of an arbitrary value accepted directly from an Android request.
    """
    if (type(trusted_binding_hash) is not str
            or not _BINDING_RE.fullmatch(trusted_binding_hash)):
        return None
    try:
        timestamp = _clock(now)
        transaction_id = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        expires_at = timestamp + CHALLENGE_TTL_SECONDS
        with _open_store(path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO google_login_challenges "
                "(transaction_id, nonce_hash, binding_hash, issued_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (transaction_id, hashlib.sha256(nonce.encode("ascii")).hexdigest(),
                 trusted_binding_hash, timestamp, expires_at),
            )
            db.execute("COMMIT")
        return LoginChallenge(transaction_id, nonce, expires_at)
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return None


def consume_challenge(path, transaction_id, nonce, trusted_binding_hash, *, now=None):
    """Burn an identified transaction on first attempt, valid or not.

    BEGIN IMMEDIATE serializes competing workers on a SINGLE shared SQLite DB.
    A bad nonce, binding or age is rejected; no retries or second authorization.
    """
    if type(transaction_id) is not str or not _TOKEN_RE.fullmatch(transaction_id):
        return False
    try:
        timestamp = _clock(now)
        with _open_store(path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT nonce_hash, binding_hash, issued_at, expires_at "
                "FROM google_login_challenges WHERE transaction_id=?",
                (transaction_id,),
            ).fetchone()
            if row is None:
                db.execute("ROLLBACK")
                return False
            db.execute(
                "DELETE FROM google_login_challenges WHERE transaction_id=?",
                (transaction_id,),
            )
            db.execute("COMMIT")
        nonce_hash, saved_binding_hash, issued_at, expires_at = row
        return (
            type(nonce) is str and _TOKEN_RE.fullmatch(nonce) is not None
            and type(trusted_binding_hash) is str
            and _BINDING_RE.fullmatch(trusted_binding_hash) is not None
            and type(nonce_hash) is str and type(saved_binding_hash) is str
            and hmac.compare_digest(
                nonce_hash, hashlib.sha256(nonce.encode("ascii")).hexdigest())
            and hmac.compare_digest(saved_binding_hash, trusted_binding_hash)
            and type(issued_at) in (int, float)
            and type(expires_at) in (int, float)
            and 0 <= timestamp - issued_at < CHALLENGE_TTL_SECONDS
            and issued_at <= timestamp < expires_at
            and 0 < expires_at - issued_at <= CHALLENGE_TTL_SECONDS
        )
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return False


def verify_and_consume_google_preflight(
    raw_token, *, path, transaction_id, nonce, trusted_binding_hash,
    client_id, trusted_public_keys, authorized_party=None, now=None
):
    """Offline composition proving a valid Google-shaped token cannot replay.

    This is NOT an endpoint and does not mint a SHAI session. A real backend
    must establish the trusted binding and fetch/rotate genuine Google keys.
    """
    if not consume_challenge(
        path, transaction_id, nonce, trusted_binding_hash, now=now
    ):
        return None
    return verify_google_id_token(
        raw_token, client_id=client_id, expected_nonce=nonce,
        trusted_public_keys=trusted_public_keys,
        authorized_party=authorized_party, now=now,
    )
