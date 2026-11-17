"""Offline-only Google ID-token signature/claim verification boundary.

This is NOT a login handler, Google-key downloader, Credential Manager integration,
session issuer, or deployed verifier. Trusted public keys and expected nonce must
come from a separately reviewed server-owned transaction. No network is used.
Never route a Google ID token directly to the SHAI /chat bearer-session verifier.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hmac
import json
import math
import re
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_GOOGLE_ISSUERS = frozenset(("accounts.google.com", "https://accounts.google.com"))
_B64URL = re.compile(r"^[A-Za-z0-9_-]{1,4096}$")
_KID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_NONCE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_SUBJECT = re.compile(r"^[A-Za-z0-9_-]{1,255}$")
_CLIENT = re.compile(r"^[A-Za-z0-9._-]{1,200}\.apps\.googleusercontent\.com$")
_MAX_TOKEN_BYTES = 8192
_MAX_GOOGLE_TOKEN_LIFETIME_SECONDS = 3900


@dataclass(frozen=True)
class VerifiedGoogleSubject:
    """Only Google's opaque stable sub; email/display names are never identity."""
    subject: str


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JWT field")
        result[key] = value
    return result


def _reject_non_json_number(value):
    raise ValueError("non-JSON number")


def _decode_segment(part):
    if not isinstance(part, str) or not _B64URL.fullmatch(part):
        raise ValueError("invalid base64url segment")
    raw = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
    if base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != part:
        raise ValueError("noncanonical segment")
    return raw


def _json_object(part):
    value = json.loads(_decode_segment(part).decode("utf-8"),
                       object_pairs_hook=_unique_fields,
                       parse_constant=_reject_non_json_number)
    if type(value) is not dict:
        raise ValueError("not a JSON object")
    return value


def verify_google_id_token(raw, *, client_id, expected_nonce,
                           trusted_public_keys, authorized_party=None, now=None):
    """Return verified Google sub or None; NEVER issue a SHAI session here.

    Public keys must be supplied by a trusted SERVER key-retrieval/cache
    mechanism; this module NEVER reads header URLs or fetches JWKS. A real
    implementation still needs Google JWKS cache expiry/key rotation, a
    server-owned one-use nonce store and a separately reviewed session issuer.
    """
    if (type(raw) is not str or len(raw) > _MAX_TOKEN_BYTES
            or type(client_id) is not str or not _CLIENT.fullmatch(client_id)
            or type(expected_nonce) is not str or not _NONCE.fullmatch(expected_nonce)
            or type(trusted_public_keys) is not dict
            or not 1 <= len(trusted_public_keys) <= 8
            or (authorized_party is not None
                and (type(authorized_party) is not str
                     or not _CLIENT.fullmatch(authorized_party)))):
        return None
    try:
        header_part, claim_part, signature_part = raw.split(".")
        header = _json_object(header_part)
        claims = _json_object(claim_part)
        if (set(header) not in ({"alg", "kid"}, {"alg", "kid", "typ"})
                or header["alg"] != "RS256"
                or ("typ" in header and header["typ"] != "JWT")
                or type(header["kid"]) is not str
                or not _KID.fullmatch(header["kid"])):
            return None
        key = trusted_public_keys.get(header["kid"])
        if (not isinstance(key, rsa.RSAPublicKey)
                or key.key_size not in (2048, 3072, 4096)
                or key.public_numbers().e != 65537):
            return None
        if (claims.get("iss") not in _GOOGLE_ISSUERS
                or type(claims.get("aud")) is not str
                or claims["aud"] != client_id
                or type(claims.get("sub")) is not str
                or not _SUBJECT.fullmatch(claims["sub"])
                or type(claims.get("nonce")) is not str
                or not hmac.compare_digest(claims["nonce"], expected_nonce)):
            return None
        azp = claims.get("azp")
        if azp is not None and (type(azp) is not str
                                or azp not in (client_id, authorized_party)):
            return None
        if type(claims.get("iat")) is not int or type(claims.get("exp")) is not int:
            return None
        if "nbf" in claims and type(claims["nbf"]) is not int:
            return None
        current = time.time() if now is None else now
        if type(current) not in (int, float) or not math.isfinite(current):
            return None
        if not (claims["iat"] <= current < claims["exp"]
                and 0 < claims["exp"] - claims["iat"] <= _MAX_GOOGLE_TOKEN_LIFETIME_SECONDS
                and ("nbf" not in claims or claims["nbf"] <= current)):
            return None
        signature = _decode_segment(signature_part)
        if len(signature) != key.key_size // 8:
            return None
        key.verify(signature,
                   (header_part + "." + claim_part).encode("ascii"),
                   padding.PKCS1v15(), hashes.SHA256())
        return VerifiedGoogleSubject(subject=claims["sub"])
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError,
            InvalidSignature, AttributeError):
        return None
