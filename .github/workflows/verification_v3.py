"""SYNTH_SHAI V3: authenticated evidence gate.
Verification is not deployment approval.
"""
import hashlib
import hmac
import json
import re
from collections.abc import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

HOLD = "144 HOLD"
REVIEW_REQUIRED = "REVIEW_REQUIRED"

_HEX = re.compile(r"^[0-9a-f]{64}$")


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_bytes(payload):
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False
    ).encode("utf-8")


def verify_result(
    record,
    *,
    trusted_keys=None,
    expected_sha256=None,
    expected_challenge=None
):
    """Verify two signed observations before human review."""

    try:
        if not isinstance(record, Mapping):
            return HOLD

        if not isinstance(trusted_keys, Mapping):
            return HOLD

        report = record.get("test_report")
        revision = record.get("source_revision")
        challenge = record.get("challenge")
        evidence = record.get("verification_evidence")

        if any(
            not isinstance(v, str) or not v.strip()
            for v in (report, revision, challenge)
        ):
            return HOLD

        if (
            not isinstance(expected_challenge, str)
            or not expected_challenge.strip()
            or challenge != expected_challenge
        ):
            return HOLD

        if (
            not isinstance(expected_sha256, str)
            or not _HEX.fullmatch(expected_sha256)
        ):
            return HOLD

        digest = sha256_text(report)

        if not hmac.compare_digest(digest, expected_sha256):
            return HOLD

        if not isinstance(evidence, list) or len(evidence) != 2:
            return HOLD

        seen_sources = set()
        seen_keys = set()
        seen_pubkeys = set()

        for entry in evidence:
            if not isinstance(entry, Mapping):
                return HOLD

            source = entry.get("source_id")
            key_id = entry.get("key_id")
            signature = entry.get("signature")

            if any(
                not isinstance(v, str) or not v.strip()
                for v in (source, key_id, signature)
            ):
                return HOLD

            if source in seen_sources or key_id in seen_keys:
                return HOLD

            if key_id not in trusted_keys:
                return HOLD

            trusted = trusted_keys[key_id]

            if (
                not isinstance(trusted, Mapping)
                or trusted.get("source_id") != source
            ):
                return HOLD

            pub = trusted.get("public_ke
