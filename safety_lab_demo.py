"""Offline, synthetic-only SYNTH_SHAI Safety Lab demonstration.

This is an educational demonstration, not an authorization service.
It generates disposable test keys and only writes a temporary SQLite replay
database. It never grants execution permission or connects to external systems.
"""
import json
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from verification_v3 import canonical_bytes, sha256_text
from verification_v3_1 import HOLD, REVIEW_REQUIRED, verify_once


def run_demo():
    """Return named results for three reproducible offline decision scenarios."""
    report = "Synthetic Safety Lab evidence only"
    revision = "safety-lab-v1"
    challenge = "safety-lab-challenge-00001"
    digest = sha256_text(report)
    trusted_keys = {}
    entries = []

    for index in (1, 2):
        key = Ed25519PrivateKey.generate()  # Disposable demo key; never persisted.
        key_id = f"demo-key-{index}"
        source_id = f"demo-source-{index}"
        public_key = key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        trusted_keys[key_id] = {"source_id": source_id, "public_key": public_key}
        payload = {
            "source_id": source_id,
            "key_id": key_id,
            "source_revision": revision,
            "report_sha256": digest,
            "challenge": challenge,
        }
        entries.append({**payload, "signature": key.sign(canonical_bytes(payload)).hex()})

    record = {
        "test_report": report,
        "source_revision": revision,
        "challenge": challenge,
        "verification_evidence": entries,
    }
    kwargs = {
        "trusted_keys": trusted_keys,
        "expected_sha256": digest,
        "expected_challenge": challenge,
    }
    with tempfile.TemporaryDirectory(prefix="shai-safety-lab-") as directory:
        database_path = str(Path(directory) / "replay.sqlite")
        # Separate missing-evidence case must never consume the challenge.
        missing = {**record, "verification_evidence": []}
        missing_result = verify_once(missing, database_path=database_path, **kwargs)
        valid_result = verify_once(record, database_path=database_path, **kwargs)
        replay_result = verify_once(record, database_path=database_path, **kwargs)

    return {
        "mode": "OFFLINE_SYNTHETIC_ONLY",
        "approval_granted": False,
        "scenarios": [
            {"case": "missing_evidence", "decision": missing_result,
             "reason": "Missing signed observations; fail closed."},
            {"case": "valid_signed_evidence", "decision": valid_result,
             "reason": "Evidence meets prototype checks; human review still required."},
            {"case": "replayed_evidence", "decision": replay_result,
             "reason": "Previously consumed challenge; fail closed."},
        ],
    }


def main():
    results = run_demo()
    print(json.dumps(results, indent=2, sort_keys=True))
    decisions = {item["case"]: item["decision"] for item in results["scenarios"]}
    expected = {
        "missing_evidence": HOLD,
        "valid_signed_evidence": REVIEW_REQUIRED,
        "replayed_evidence": HOLD,
    }
    return 0 if decisions == expected and results["approval_granted"] is False else 1


if __name__ == "__main__":
    raise SystemExit(main())
