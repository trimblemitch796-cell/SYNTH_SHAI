"""Offline, fail-closed adapter for SYNTH_SHAI V3.1 evidence verification.
Requires verification_v3.py and verification_v3_1.py from the SYNTH_SHAI repo.
No ChatGPT API, network traffic, actuation, payment, or authorization.
"""
import argparse
import json
from pathlib import Path
from verification_v3 import HOLD, REVIEW_REQUIRED
from verification_v3_1 import verify_once


def evaluate(envelope, *, db_path):
    """Return only HOLD or REVIEW_REQUIRED. No approvals are issued."""
    try:
        if not isinstance(envelope, dict) or set(envelope) != {"record", "trusted_keys", "expected_sha256", "expected_challenge"}:
            return HOLD
        record = envelope["record"]
        raw_keys = envelope["trusted_keys"]
        if not isinstance(raw_keys, dict) or len(raw_keys) != 2:
            return HOLD
        keys = {}
        for key_id, item in raw_keys.items():
            if not isinstance(item, dict) or set(item) != {"source_id", "public_key_hex"}:
                return HOLD
            public = item["public_key_hex"]
            if not isinstance(public, str) or len(public) != 64 or any(c not in '0123456789abcdef' for c in public):
                return HOLD
            keys[key_id] = {"source_id": item["source_id"], "public_key": bytes.fromhex(public)}
        return verify_once(record, database_path=db_path, trusted_keys=keys,
                           expected_sha256=envelope["expected_sha256"],
                           expected_challenge=envelope["expected_challenge"])
    except (TypeError, ValueError, KeyError, OSError):
        return HOLD


def main():
    parser = argparse.ArgumentParser(description='SYNTH_SHAI V3.1 offline evidence gate')
    parser.add_argument('--input', required=True, type=Path, help='Local JSON envelope')
    parser.add_argument('--replay-db', required=True, type=Path, help='Persistent local SQLite replay database')
    args = parser.parse_args()
    result = HOLD
    try:
        # Limit input size before parsing to bound worst-case memory use.
        if args.input.stat().st_size > 1_200_000:
            raise ValueError('Input exceeds 1.2MB')
        envelope = json.loads(args.input.read_text(encoding='utf-8'))
        result = evaluate(envelope, db_path=args.replay_db)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        pass
    print(json.dumps({'decision': result, 'approval_granted': False}, sort_keys=True))
    return 0 if result == REVIEW_REQUIRED else 2


if __name__ == '__main__':
    raise SystemExit(main())
