"""Research-only, fail-closed text payload binding for offline synthetic review.

Experimental branch integration: offline_worker_v3.worker_once calls this adapter.
Existing in-process dispatch_simulation is still separately callable by trusted
code; host isolation and real-world execution controls remain outside scope.
Unknown encodings, ambiguity, malformed input and any incomplete verification HOLD.
"""

import base64
import binascii
import hashlib
import hmac
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote_to_bytes

from offline_approval_v1 import HOLD, _valid_request
from offline_dispatch_v3 import dispatch_simulation

MAX_RAW_BYTES = 16_384
MAX_CANONICAL_BYTES = 16_384
MAX_DEPTH = 3
B64_PATTERN = re.compile(rb"(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?\Z")
PERCENT_ESCAPE = re.compile(rb"%[0-9A-Fa-f]{2}")
BAD_PERCENT = re.compile(rb"%(?![0-9A-Fa-f]{2})")
UNICODE_ESCAPE = re.compile(rb"\\(?:u[0-9A-Fa-f]{4}|x[0-9A-Fa-f]{2})")
# A synthetic marker used solely to test the behavior of a placeholder policy.
SYNTHETIC_DENY_MARKER = b"SYNTHETIC_CONFIDENTIAL_EXAMPLE"


class NormalizeHold(ValueError):
    """Untrusted/unresolvable text, conservatively refused."""


@dataclass(frozen=True)
class CanonicalText:
    payload: bytes
    sha256: str


def _check_size(data: bytes) -> None:
    if len(data) == 0 or len(data) > MAX_CANONICAL_BYTES:
        raise NormalizeHold("empty_or_oversized")


def _valid_utf8(data: bytes) -> None:
    try:
        data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise NormalizeHold("not_utf8_text") from exc


def _strict_base64(data: bytes) -> bytes:
    if len(data) < 4 or len(data) % 4 != 0 or B64_PATTERN.fullmatch(data) is None:
        raise NormalizeHold("invalid_base64")
    try:
        decoded = base64.b64decode(data, validate=True)
    except binascii.Error as exc:
        raise NormalizeHold("invalid_base64") from exc
    if base64.b64encode(decoded) != data:
        raise NormalizeHold("noncanonical_base64")
    return decoded


def _looks_like_another_layer(data: bytes) -> bool:
    if PERCENT_ESCAPE.search(data) or UNICODE_ESCAPE.search(data):
        return True
    # Conservative heuristic, not a complete obfuscation detector. A legitimate
    # base64-looking literal may HOLD. An explicit human review is then needed.
    try:
        decoded = _strict_base64(data)
        _valid_utf8(decoded)
        return decoded.decode("utf-8").isprintable()
    except NormalizeHold:
        return False


def _policy_view(payload: bytes) -> bytes:
    """Conservative policy scan only; never change signed canonical bytes.

    Reject non-rendered formatting/controls (except ordinary multiline text),
    then NFKC-fold compatibility glyphs for synthetic marker comparison.
    This does not establish complete Unicode confusable or DLP coverage.
    """
    text = payload.decode("utf-8", errors="strict")
    if any(unicodedata.category(char) in ("Cc", "Cf", "Cs")
           and char not in "\n\r\t" for char in text):
        raise NormalizeHold("invisible_or_control_character")
    return unicodedata.normalize("NFKC", text).upper().encode("utf-8")


def normalize_explicit_text(raw_payload: bytes, encodings: tuple[str, ...]) -> CanonicalText:
    """Decode only an explicitly declared outer-to-inner chain; no guess-and-allow.

    Every layer and terminal text must be valid UTF-8. The terminal exact UTF-8
    bytes are hashed without Unicode case folding or NFC transformation.
    This is an explicit, versioned *research* text-only policy.
    """
    if type(raw_payload) is not bytes or not 0 < len(raw_payload) <= MAX_RAW_BYTES:
        raise NormalizeHold("invalid_raw_payload")
    if type(encodings) is not tuple or len(encodings) > MAX_DEPTH:
        raise NormalizeHold("invalid_encoding_chain")
    if any(type(enc) is not str or enc not in ("base64", "percent") for enc in encodings):
        raise NormalizeHold("unknown_encoding")
    text = raw_payload
    _valid_utf8(text)
    for step in encodings:
        if step == "base64":
            text = _strict_base64(text)
        elif step == "percent":
            if b"%" not in text or BAD_PERCENT.search(text):
                raise NormalizeHold("invalid_percent_encoding")
            decoded = unquote_to_bytes(text)
            if decoded == text:
                raise NormalizeHold("percent_layer_not_present")
            text = decoded
        _check_size(text)
        _valid_utf8(text)
    _check_size(text)
    # Refuse unresolved / undeclared layers, rather than treat encoded content
    # as harmless plaintext. This may conservatively reject ambiguous literals.
    if _looks_like_another_layer(text):
        raise NormalizeHold("ambiguous_or_unresolved_layer")
    _policy_view(text)  # Reject unrendered controls before any signature is consumed.
    return CanonicalText(text, hashlib.sha256(text).hexdigest())


def guarded_synthetic_review(request, approval, *, raw_payload, encodings,
                             policy, trusted_operator_keys, trusted_database_path, now):
    """Optional *test-only* adapter; never grants real permission.

    Worker entrypoint is required to call this adapter on the research branch.
    In-process callers could still invoke dispatch_simulation directly; do not
    advertise whole-system enforcement. The deny marker is not a DLP tool.
    """
    try:
        if not _valid_request(request) or request["action"] != "synthetic_review":
            return HOLD
        canonical = normalize_explicit_text(raw_payload, encodings)
        if not hmac.compare_digest(request["plan_sha256"], canonical.sha256):
            return HOLD
        if SYNTHETIC_DENY_MARKER in _policy_view(canonical.payload):
            return HOLD
        return dispatch_simulation(
            request, approval, policy=policy,
            trusted_operator_keys=trusted_operator_keys,
            trusted_database_path=trusted_database_path, now=now).decision
    except (NormalizeHold, ValueError, TypeError, KeyError, AttributeError):
        return HOLD
