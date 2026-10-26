"""Offline, fail-closed adapter for SYNTH_SHAI V3.1 evidence verification.
Requires verification_v3.py and verification_v3_1.py from the SYNTH_SHAI repo.
No ChatGPT API, network traffic, actuation, payment, or authorization.
"""
import argparse
import json
from pathlib import Path
from verification_v3 import HOLD, REVIEW_REQUIRED
from verification_v3_1 import verify_once


ENVELOPE_FIELDS = {"record"}   # trust material is NEVER taken from the envelope


class TrustConfig:
    """Pinned trusted signing keys, held by the VERIFIER (trusted configuration).

    trusted_keys: {key_id: {"source_id": str, "public_key_hex": 64 hex chars}}
    Validated when used; anything malformed fails closed to HOLD. The envelope
    being verified can never add, replace or remove keys.
    """
    __slots__ = ("_raw",)

    def __init__(self, trusted_keys):
        object.__setattr__(self, "_raw", json.loads(json.dumps(trusted_keys)))  # private copy

    def __setattr__(self, name, value):
        raise AttributeError("TrustConfig is read-only")

    def parsed_keys(self):
        raw = self._raw
        if not isinstance(raw, dict) or len(raw) != 2:
            raise ValueError("exactly two pinned keys required")
        keys = {}
        for key_id, item in raw.items():
            if not isinstance(item, dict) or set(item) != {"source_id", "public_key_hex"}:
                raise ValueError("malformed pinned key")
            public = item["public_key_hex"]
            if not isinstance(public, str) or len(public) != 64 or any(c not in '0123456789abcdef' for c in public):
                raise ValueError("malformed pinned key")
            keys[key_id] = {"source_id": item["source_id"], "public_key": bytes.fromhex(public)}
        return keys


def load_trust_config(path):
    """Read pinned keys from a local JSON file: {"trusted_keys": {...}}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"trusted_keys"}:
        raise ValueError("trust config must be exactly {'trusted_keys': {...}}")
    return TrustConfig(data["trusted_keys"])


def evaluate(envelope, *, db_path, trust=None, expected_challenge=None, expected_sha256=None):
    """Return only HOLD or REVIEW_REQUIRED. No approvals are issued.

    trust: TrustConfig of pinned keys (verifier's trusted configuration).
    expected_challenge: the challenge the VERIFIER issued for this evidence.
    expected_sha256: the report hash the VERIFIER expects.
    The envelope must be exactly {"record": ...}; an envelope that tries to
    supply its own keys, hash or challenge is refused. Missing trust -> HOLD.
    """
    try:
        if not isinstance(trust, TrustConfig):
            return HOLD
        if type(expected_challenge) is not str or type(expected_sha256) is not str:
            return HOLD
        if not isinstance(envelope, dict) or set(envelope) != ENVELOPE_FIELDS:
            return HOLD
        keys = trust.parsed_keys()
        return verify_once(envelope["record"], database_path=db_path, trusted_keys=keys,
                           expected_sha256=expected_sha256,
                           expected_challenge=expected_challenge)
    except (TypeError, ValueError, KeyError, OSError):
        return HOLD


def main():
    parser = argparse.ArgumentParser(description='SYNTH_SHAI V3.1 offline evidence gate')
    parser.add_argument('--input', required=True, type=Path, help='Local JSON envelope')
    parser.add_argument('--replay-db', required=True, type=Path, help='Persistent local SQLite replay database')
    parser.add_argument('--trust-config', required=True, type=Path,
                        help='Local JSON {"trusted_keys": {...}} of pinned signing keys (verifier-held)')
    parser.add_argument('--challenge', required=True, help='Challenge the verifier issued for this evidence')
    parser.add_argument('--expected-sha256', required=True, help='Report SHA-256 the verifier expects')
    args = parser.parse_args()
    result = HOLD
    try:
        # Limit input size before parsing to bound worst-case memory use.
        if args.input.stat().st_size > 1_200_000:
            raise ValueError('Input exceeds 1.2MB')
        envelope = json.loads(args.input.read_text(encoding='utf-8'))
        result = evaluate(envelope, db_path=args.replay_db,
                          trust=load_trust_config(args.trust_config),
                          expected_challenge=args.challenge, expected_sha256=args.expected_sha256)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError, RecursionError):
        pass
    print(json.dumps({'decision': result, 'approval_granted': False}, sort_keys=True))
    return 0 if result == REVIEW_REQUIRED else 2


if __name__ == '__main__':
    raise SystemExit(main())
