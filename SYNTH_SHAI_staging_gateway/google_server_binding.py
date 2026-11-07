"""Server-owned, ephemeral *pre-authentication* session binding (offline review).

NOT a public HTTP endpoint or Android native sign-in. This module generates
the cookie itself, stores only a digest in trusted SQLite, derives challenge
ownership from a verified cookie and consumes the session before token checks.
A future BFF/HTTPS endpoint MUST independently enforce trusted Host/TLS,
Origin/CSRF, proxy configuration and Google token/session issuance.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import hashlib
import math
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit

from .google_login_challenge import (
    CHALLENGE_TTL_SECONDS, _open_store, initialize_challenge_store,
    issue_challenge, verify_and_consume_google_preflight,
)

COOKIE_NAME = "__Host-SHAI-Login"
SESSION_SECONDS = 300
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")
_SET_COOKIE_SUFFIX = "; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=300"
CLEAR_COOKIE = COOKIE_NAME + "=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0"


@dataclass(frozen=True, repr=False)
class PreauthCookie:
    """Treat cookie_value as a secret: never log or put in URL."""
    cookie_value: str
    set_cookie: str

    def __repr__(self):
        return "PreauthCookie(<redacted>)"


def _clock(now):
    stamp = time.time() if now is None else now
    if type(stamp) not in (float, int) or not math.isfinite(stamp) or stamp < 0:
        raise ValueError("untrusted clock")
    return float(stamp)


def _cookie_hash(cookie_header):
    if type(cookie_header) is not str or not 1 <= len(cookie_header) <= 4096:
        return None
    if any(ord(c) < 32 or ord(c) > 126 for c in cookie_header):
        return None
    selected = []
    for item in cookie_header.split(";"):
        part = item.strip()
        if "=" not in part:
            return None
        name, value = part.split("=", 1)
        if name == COOKIE_NAME:
            selected.append(value)
    if len(selected) != 1 or not _TOKEN.fullmatch(selected[0]):
        return None
    return hashlib.sha256(selected[0].encode("ascii")).hexdigest()


def _trusted_origin(request_origin, configured_origin):
    if type(request_origin) is not str or type(configured_origin) is not str:
        return False
    if request_origin != configured_origin or len(configured_origin) > 256:
        return False
    parsed = urlsplit(configured_origin)
    return (parsed.scheme == "https" and parsed.hostname is not None
            and parsed.username is None and parsed.password is None
            and not parsed.path and not parsed.query and not parsed.fragment)


def initialize_preauth_store(path):
    """Trusted operator setup, never an incoming HTTP request."""
    initialize_challenge_store(path)
    with closing(_open_store(path)) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS server_preauth_sessions ("
            "cookie_hash TEXT PRIMARY KEY, created_at REAL NOT NULL, "
            "expires_at REAL NOT NULL, started INTEGER NOT NULL DEFAULT 0 "
            "CHECK(started IN (0, 1)))")


def issue_preauth_cookie(path, *, now=None):
    """Generate opaque server-owned random cookie and persist only its digest."""
    try:
        stamp = _clock(now)
        token = secrets.token_urlsafe(32)
        if not _TOKEN.fullmatch(token):
            return None
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        with closing(_open_store(path)) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO server_preauth_sessions "
                "(cookie_hash, created_at, expires_at) VALUES (?, ?, ?)",
                (digest, stamp, stamp + SESSION_SECONDS))
            db.execute("COMMIT")
        return PreauthCookie(token, COOKIE_NAME + "=" + token + _SET_COOKIE_SUFFIX)
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return None


def _live(row, now, *, started=None):
    if row is None:
        return False
    created, expires, was_started = row
    return (type(created) in (int, float) and type(expires) in (int, float)
            and math.isfinite(created) and math.isfinite(expires)
            and 0 <= now - created < SESSION_SECONDS
            and created <= now < expires
            and 0 < expires - created <= SESSION_SECONDS
            and (started is None or was_started == started))


def start_bound_google_login(path, cookie_header, *, request_origin,
                             configured_origin, now=None):
    """Derive binding from authenticated server-issued cookie, not a client hash.

    One challenge per preauth cookie. 'started' reserved atomically; if
    challenge insertion fails the session remains consumed for starting.
    """
    digest = _cookie_hash(cookie_header)
    if digest is None or not _trusted_origin(request_origin, configured_origin):
        return None
    try:
        stamp = _clock(now)
        with closing(_open_store(path)) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT created_at, expires_at, started "
                "FROM server_preauth_sessions WHERE cookie_hash=?", (digest,)
            ).fetchone()
            if not _live(row, stamp, started=0):
                db.execute("ROLLBACK")
                return None
            db.execute(
                "UPDATE server_preauth_sessions SET started=1 WHERE cookie_hash=?",
                (digest,))
            db.execute("COMMIT")
        return issue_challenge(path, digest, now=stamp)
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return None


def finish_bound_google_login(
    path, cookie_header, *, request_origin, configured_origin, transaction_id,
    nonce, raw_google_token, client_id, trusted_public_keys,
    authorized_party=None, now=None
):
    """One-use preauth session + challenge + synthetic Google token verification.

    Only a trusted HTTPS/BFF adapter may supply request_origin,
    configured_origin, Google public keys, client_id and session cookie.
    Does not mint a SHAI JWT, authenticate an Android native app, or
    connect /chat to Google. Caller should emit CLEAR_COOKIE on completion.
    """
    digest = _cookie_hash(cookie_header)
    if digest is None or not _trusted_origin(request_origin, configured_origin):
        return None
    try:
        stamp = _clock(now)
        with closing(_open_store(path)) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT created_at, expires_at, started "
                "FROM server_preauth_sessions WHERE cookie_hash=?", (digest,)
            ).fetchone()
            if not _live(row, stamp, started=1):
                db.execute("ROLLBACK")
                return None
            # Burn cookie before any external verification. No callback replay.
            db.execute(
                "DELETE FROM server_preauth_sessions WHERE cookie_hash=?", (digest,))
            db.execute("COMMIT")
        return verify_and_consume_google_preflight(
            raw_google_token, path=path, transaction_id=transaction_id,
            nonce=nonce, trusted_binding_hash=digest, client_id=client_id,
            trusted_public_keys=trusted_public_keys,
            authorized_party=authorized_party, now=stamp,
        )
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return None


def revoke_preauth_cookie(path, cookie_header):
    """Operator-controlled logout; returns False on missing/failing store."""
    digest = _cookie_hash(cookie_header)
    if digest is None:
        return False
    try:
        with closing(_open_store(path)) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "DELETE FROM server_preauth_sessions WHERE cookie_hash=?", (digest,))
            db.execute("COMMIT")
        return True
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return False



def finish_bound_google_login_with_cached_google_keys(
    path, cookie_header, *, request_origin, configured_origin,
    transaction_id, nonce, raw_google_token, client_id,
    google_key_cache, authorized_party=None, now=None, cache_now=None
):
    """Compose trusted server-owned binding with fresh pinned Google keys.

    A missing/stale/bad cache denies the callback and BURNS the preauth cookie.
    Do not accept a public-key dictionary from HTTP callers or JWT headers.
    No real issuer, Android session exchange, or external tools are exposed.
    """
    from .google_jwks_rotation import GoogleJwksCache, JwksRejected

    keys = {}
    if isinstance(google_key_cache, GoogleJwksCache):
        try:
            keys = google_key_cache.snapshot(now=cache_now)
        except JwksRejected:
            keys = {}
    return finish_bound_google_login(
        path, cookie_header, request_origin=request_origin,
        configured_origin=configured_origin,
        transaction_id=transaction_id, nonce=nonce,
        raw_google_token=raw_google_token, client_id=client_id,
        trusted_public_keys=keys, authorized_party=authorized_party, now=now
    )
