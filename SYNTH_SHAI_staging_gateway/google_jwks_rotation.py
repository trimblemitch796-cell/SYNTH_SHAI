"""Bounded Google JWKS rotation cache. No automatic network activity.

Official discovery pins https://www.googleapis.com/oauth2/v3/certs.
No request-time unknown-kid fetch, no tokeninfo fallback and no stale-key grace.
The HTTPS fetcher is OPTIONAL and never called in the offline test suite or
the /chat service. No live Google client, auth endpoint or session issuer.
"""
from __future__ import annotations

import base64
import json
import math
import re
import threading
import time
from urllib import error, request

from cryptography.hazmat.primitives.asymmetric import rsa

GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
MAX_JWKS_BYTES = 65536
MAX_CACHE_SECONDS = 86400
_KID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_B64 = re.compile(r"^[A-Za-z0-9_-]{1,1024}$")


class JwksRejected(ValueError):
    pass


def _no_duplicates(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise JwksRejected("duplicate JSON key")
        obj[k] = v
    return obj


def _decode_uint(raw):
    if type(raw) is not str or not _B64.fullmatch(raw):
        raise JwksRejected("invalid canonical base64url integer")
    try:
        payload = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise JwksRejected("invalid encoding") from exc
    if (not payload or payload[0] == 0
            or base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=") != raw):
        raise JwksRejected("noncanonical integer")
    return int.from_bytes(payload, "big")


def parse_google_jwks(raw):
    """Parse bounded, strict RS256 keys. Caller MUST establish Google provenance."""
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_JWKS_BYTES:
        raise JwksRejected("invalid JWKS size")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates,
                             parse_constant=lambda value: (_ for _ in ()).throw(
                                 JwksRejected("invalid JSON constant")))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise JwksRejected("invalid JWKS JSON") from exc
    if (type(payload) is not dict or set(payload) != {"keys"}
            or type(payload["keys"]) is not list
            or not 1 <= len(payload["keys"]) <= 8):
        raise JwksRejected("unexpected Google JWKS structure")
    result = {}
    for item in payload["keys"]:
        if (type(item) is not dict
                or set(item) != {"kty", "alg", "use", "kid", "n", "e"}
                or item["kty"] != "RSA" or item["alg"] != "RS256"
                or item["use"] != "sig" or type(item["kid"]) is not str
                or not _KID.fullmatch(item["kid"])
                or item["kid"] in result):
            raise JwksRejected("unexpected or duplicate signing key")
        exponent = _decode_uint(item["e"])
        modulus = _decode_uint(item["n"])
        if exponent != 65537 or modulus.bit_length() not in (2048, 3072, 4096):
            raise JwksRejected("unapproved RSA key profile")
        try:
            public = rsa.RSAPublicNumbers(exponent, modulus).public_key()
        except ValueError as exc:
            raise JwksRejected("invalid RSA key") from exc
        result[item["kid"]] = public
    return result


def _max_age(cache_control):
    """Require one positive HTTP max-age; no-store/no-cache/private fail closed."""
    if type(cache_control) is not str or len(cache_control) > 1024:
        raise JwksRejected("missing cache control")
    directives = [part.strip().lower() for part in cache_control.split(",")]
    if any(x in directives for x in ("no-store", "no-cache", "private")):
        raise JwksRejected("uncacheable keys")
    matches = [x for x in directives if x.startswith("max-age")]
    if len(matches) != 1 or not re.fullmatch(r"max-age=[0-9]{1,8}", matches[0]):
        raise JwksRejected("invalid max-age")
    age = int(matches[0].split("=", 1)[1])
    if age <= 0:
        raise JwksRejected("expired on arrival")
    return min(age, MAX_CACHE_SECONDS)


def _clock(now):
    stamp = time.monotonic() if now is None else now
    if type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < 0:
        raise JwksRejected("invalid monotonic clock")
    return float(stamp)


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_pinned_google_jwks(*, opener=None):
    """Optional trusted-host HTTPS fetch, no redirects; NEVER called by default.

    TLS uses OS certificate trust. Network/proxy isolation, egress policy and
    trusted local configuration still require independent operational review.
    """
    http = opener if opener is not None else request.build_opener(_NoRedirect())
    req = request.Request(
        GOOGLE_JWKS_URI, headers={"Accept": "application/json"}, method="GET")
    try:
        with http.open(req, timeout=6) as response:
            url = response.geturl()
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            cache_control = response.headers.get("Cache-Control", "")
            if (url != GOOGLE_JWKS_URI or status != 200
                    or content_type.split(";", 1)[0].strip().lower() != "application/json"):
                raise JwksRejected("untrusted JWKS HTTPS response")
            body = response.read(MAX_JWKS_BYTES + 1)
    except (OSError, ValueError, error.HTTPError) as exc:
        raise JwksRejected("Google JWKS fetch failed") from exc
    return body, cache_control, url


class GoogleJwksCache:
    """Operator-refreshable in-memory keys with atomic rotation and hard expiry."""
    def __init__(self):
        self._lock = threading.Lock()
        self._keys = {}
        self._expires_at = 0.0

    def install_trusted_response(self, body, cache_control, fetched_url, *, now=None):
        """Only call with results from the pinned trusted HTTPS fetcher."""
        if fetched_url != GOOGLE_JWKS_URI:
            raise JwksRejected("untrusted JWKS URL")
        stamp = _clock(now)
        public_keys = parse_google_jwks(body)
        ttl = _max_age(cache_control)
        with self._lock:
            self._keys = public_keys
            self._expires_at = stamp + ttl
        return len(public_keys)

    def refresh(self, *, opener=None, now=None):
        body, cache_control, url = fetch_pinned_google_jwks(opener=opener)
        return self.install_trusted_response(body, cache_control, url, now=now)

    def snapshot(self, *, now=None):
        stamp = _clock(now)
        with self._lock:
            if not self._keys or stamp >= self._expires_at:
                return {}
            return dict(self._keys)


def verify_with_cached_google_keys(raw_token, cache, *, client_id, expected_nonce,
                                   authorized_party=None, now=None,
                                   cache_now=None):
    """Explicit opt-in offline composition; does not issue a SHAI session."""
    from .google_oidc_preflight import verify_google_id_token
    if not isinstance(cache, GoogleJwksCache):
        return None
    try:
        keys = cache.snapshot(now=cache_now)
    except JwksRejected:
        return None
    if not keys:
        return None
    return verify_google_id_token(
        raw_token, client_id=client_id, expected_nonce=expected_nonce,
        trusted_public_keys=keys, authorized_party=authorized_party, now=now)
