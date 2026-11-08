"""Offline review-only short-lived Ed25519 session checks and durable quotas.

NOT an OAuth authorization server or identity provider. A trusted issuer must
authenticate the human and mint tokens outside this service. Neither signing
keys nor OpenAI keys belong in a client or this repository.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import quote, urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_SESSION_SECONDS = 15 * 60
MAX_TOTAL_REQUESTS = 30
MAX_USER_REQUESTS = 10
MAX_GLOBAL_MINUTE = 6
MAX_USER_MINUTE = 3
SESSION_RE = re.compile(r"^[A-Za-z0-9_-]+$")
IDENTITY_RE = re.compile(r"^[A-Za-z0-9:_-]{1,128}$")


@dataclass(frozen=True)
class Session:
    subject: str
    jti: str


def _no_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON field")
        value[key] = item
    return value


def _decode(piece):
    if not isinstance(piece, str) or not 1 <= len(piece) <= 4096 or not SESSION_RE.fullmatch(piece):
        raise ValueError("invalid base64url")
    raw = base64.urlsafe_b64decode(piece + "=" * (-len(piece) % 4))
    if base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != piece:
        raise ValueError("noncanonical base64url")
    return raw


def settings_ready():
    try:
        issuer = os.environ["SHAI_SESSION_ISSUER"]
        audience = os.environ["SHAI_SESSION_AUDIENCE"]
        raw_key = os.environ["SHAI_SESSION_PUBLIC_KEY_HEX"]
        path = os.environ["SHAI_GATEWAY_DB"]
        url = urlsplit(issuer)
        return (url.scheme == "https" and bool(url.hostname) and not url.username
                and not url.password and not url.fragment and not url.query
                and len(audience) >= 4 and len(audience) <= 128
                and re.fullmatch(r"[0-9a-fA-F]{64}", raw_key) is not None
                and isinstance(path, str) and Path(path).is_absolute()
                and Path(path).is_file())
    except (KeyError, ValueError, OSError):
        return False


def verify_session_token(raw, *, now=None):
    """Verify pinned EdDSA JWT. Return trusted identity or None, never unverified claims."""
    if not settings_ready() or not isinstance(raw, str) or len(raw) > 4096:
        return None
    try:
        header_part, claims_part, sig_part = raw.split(".")
        header = json.loads(_decode(header_part), object_pairs_hook=_no_duplicate_keys)
        claims = json.loads(_decode(claims_part), object_pairs_hook=_no_duplicate_keys)
        if header != {"alg": "EdDSA", "typ": "JWT"} or type(claims) is not dict:
            return None
        if set(claims) != {"iss", "aud", "sub", "jti", "iat", "nbf", "exp"}:
            return None
        if claims["iss"] != os.environ["SHAI_SESSION_ISSUER"]:
            return None
        if claims["aud"] != os.environ["SHAI_SESSION_AUDIENCE"]:
            return None
        if not all(type(claims[k]) is str and IDENTITY_RE.fullmatch(claims[k])
                   for k in ("sub", "jti")):
            return None
        if not all(type(claims[k]) is int for k in ("iat", "nbf", "exp")):
            return None
        current = time.time() if now is None else now
        if type(current) not in (int, float) or not math.isfinite(current):
            return None
        if not (claims["iat"] <= current and claims["nbf"] <= current < claims["exp"]
                and 0 < claims["exp"] - claims["iat"] <= MAX_SESSION_SECONDS
                and claims["nbf"] <= claims["exp"]):
            return None
        signature = _decode(sig_part)
        if len(signature) != 64:
            return None
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(
            os.environ["SHAI_SESSION_PUBLIC_KEY_HEX"]
        ))
        key.verify(signature, (header_part + "." + claims_part).encode("ascii"))
        return Session(subject=claims["sub"], jti=claims["jti"])
    except (KeyError, ValueError, TypeError, UnicodeError, InvalidSignature, OverflowError):
        return None


def _trusted_path(path):
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise ValueError("operator-controlled absolute SQLite path required")
    return path


def initialize_store(path):
    """Operator-only provisioning. Never call on incoming requests."""
    path = _trusted_path(path)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS revoked (jti_hash TEXT PRIMARY KEY)")
        db.execute("CREATE TABLE IF NOT EXISTS accepted (id INTEGER PRIMARY KEY, subject_hash TEXT NOT NULL, at REAL NOT NULL)")
        db.execute("CREATE INDEX IF NOT EXISTS accepted_subject ON accepted(subject_hash, at)")


def revoke_session(path, jti):
    """Local trusted-host operation: revoke a session; not exposed over HTTP."""
    if type(jti) is not str or not IDENTITY_RE.fullmatch(jti):
        raise ValueError("invalid token identifier")
    path = _trusted_path(path)
    with sqlite3.connect("file:" + quote(path) + "?mode=rw", uri=True) as db:
        db.execute("INSERT OR IGNORE INTO revoked(jti_hash) VALUES (?)",
                   (hashlib.sha256(jti.encode()).hexdigest(),))


def reserve_request(identity: Session, *, now=None):
    """Atomic, cross-process quota on ONE durable SQLite file. Fail closed."""
    if not isinstance(identity, Session) or not settings_ready():
        return "unavailable"
    timestamp = time.time() if now is None else now
    if type(timestamp) not in (int, float) or not math.isfinite(timestamp):
        return "unavailable"
    path = os.environ["SHAI_GATEWAY_DB"]
    user_hash = hashlib.sha256(identity.subject.encode()).hexdigest()
    jti_hash = hashlib.sha256(identity.jti.encode()).hexdigest()
    try:
        with sqlite3.connect("file:" + quote(path) + "?mode=rw",
                             timeout=2, isolation_level=None, uri=True) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if db.execute("SELECT 1 FROM revoked WHERE jti_hash=?", (jti_hash,)).fetchone():
                    db.execute("ROLLBACK")
                    return "revoked"
                total = db.execute("SELECT COUNT(*) FROM accepted").fetchone()[0]
                user_total = db.execute("SELECT COUNT(*) FROM accepted WHERE subject_hash=?", (user_hash,)).fetchone()[0]
                recent = db.execute("SELECT COUNT(*) FROM accepted WHERE at>?", (timestamp - 60,)).fetchone()[0]
                user_recent = db.execute("SELECT COUNT(*) FROM accepted WHERE subject_hash=? AND at>?",
                                         (user_hash, timestamp - 60)).fetchone()[0]
                if (total >= MAX_TOTAL_REQUESTS or user_total >= MAX_USER_REQUESTS
                        or recent >= MAX_GLOBAL_MINUTE or user_recent >= MAX_USER_MINUTE):
                    db.execute("ROLLBACK")
                    return "limited"
                db.execute("INSERT INTO accepted(subject_hash, at) VALUES (?, ?)", (user_hash, timestamp))
                db.execute("COMMIT")
                return "accepted"
            except Exception:
                db.execute("ROLLBACK")
                raise
    except (sqlite3.Error, OSError, ValueError):
        return "unavailable"
