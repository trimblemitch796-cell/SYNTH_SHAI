"""SYNTH_SHAI V3.1 offline CATHARSIS tests.

Test-only keys are generated locally. Never use production private keys.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from verification_v3 import canonical_bytes, sha256_text
from verification_v3_1 import HOLD, REVIEW_REQUIRED, verify_result, verify_once


class CatharsisV31Tests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = str(Path(self.temp.name) / "replay.sqlite")

        self.report = "SYNTH_SHAI offline test report"
        self.revision = "abc123"
        self.challenge = "challenge-1234567890123456"
        self.digest = sha256_text(self.report)

        self.keys = [
            Ed25519PrivateKey.generate(),
            Ed25519PrivateKey.generate(),
        ]

        self.trusted = {}
        self.entries = []

        for i, private_key in enumerate(self.keys):
            source = f"source-{i + 1}"
            key_id = f"key-{i + 1}"

            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )

            self.trusted[key_id] = {
                "source_id": source,
                "public_key": public_key,
            }

            payload = {
                "source_id": source,
                "key_id": key_id,
                "source_revision": self.revision,
                "report_sha256": self.digest,
                "challenge": self.challenge,
            }

            signature = private_key.sign(canonical_bytes(payload))
            self.entries.append({
                **payload,
                "signature": signature.hex(),
            })

        self.record = {
            "test_report": self.report,
            "source_revision": self.revision,
            "challenge": self.challenge,
            "verification_evidence": self.entries,
        }

        self.arguments = {
            "trusted_keys": self.trusted,
            "expected_sha256": self.digest,
            "expected_challenge": self.challenge,
        }

    def check(self, record):
        return verify_result(record, **self.arguments)

    def test_01_valid_evidence_requires_review(self):
        self.assertEqual(
            self.check(self.record),
            REVIEW_REQUIRED,
        )

    def test_02_missing_record_holds(self):
        self.assertEqual(self.check(None), HOLD)

    def test_03_extra_field_holds(self):
        record = copy.deepcopy(self.record)
        record["operator_approval"] = True
        self.assertEqual(self.check(record), HOLD)

    def test_04_empty_report_holds(self):
        record = copy.deepcopy(self.record)
        record["test_report"] = ""
        self.assertEqual(self.check(record), HOLD)

    def test_05_oversized_report_holds(self):
        record = copy.deepcopy(self.record)
        record["test_report"] = "x" * 1_000_001
        self.assertEqual(self.check(record), HOLD)

    def test_06_invalid_revision_holds(self):
        record = copy.deepcopy(self.record)
        record["source_revision"] = "invalid revision"
        self.assertEqual(self.check(record), HOLD)

    def test_07_short_challenge_holds(self):
        record = copy.deepcopy(self.record)
        record["challenge"] = "short"
        self.assertEqual(self.check(record), HOLD)

    def test_08_wrong_digest_holds(self):
        arguments = dict(self.arguments)
        arguments["expected_sha256"] = "0" * 64
        self.assertEqual(
            verify_result(self.record, **arguments),
            HOLD,
        )

    def test_09_wrong_challenge_holds(self):
        arguments = dict(self.arguments)
        arguments["expected_challenge"] = "different-challenge-123456"
        self.assertEqual(
            verify_result(self.record, **arguments),
            HOLD,
        )

    def test_10_tampered_report_holds(self):
        record = copy.deepcopy(self.record)
        record["test_report"] = "Altered report"
        self.assertEqual(self.check(record), HOLD)

    def test_11_forged_signature_holds(self):
        record = copy.deepcopy(self.record)
        record["verification_evidence"][0]["signature"] = "00" * 64
        self.assertEqual(self.check(record), HOLD)

    def test_12_untrusted_key_holds(self):
        trusted = dict(self.trusted)
        trusted.pop("key-2")
        self.assertEqual(
            verify_result(
                self.record,
                trusted_keys=trusted,
                expected_sha256=self.digest,
                expected_challenge=self.challenge,
            ),
            HOLD,
        )

    def test_13_duplicate_source_holds(self):
        record = copy.deepcopy(self.record)
        record["verification_evidence"][1]["source_id"] = "source-1"
        self.assertEqual(self.check(record), HOLD)

    def test_14_repeated_challenge_holds(self):
        first = verify_once(
            self.record,
            database_path=self.database,
            **self.arguments,
        )
        second = verify_once(
            self.record,
            database_path=self.database,
            **self.arguments,
        )
        self.assertEqual(first, REVIEW_REQUIRED)
        self.assertEqual(second, HOLD)

    def test_15_replay_after_process_restart_holds(self):
        first = verify_once(
            self.record,
            database_path=self.database,
            **self.arguments,
        )
        self.assertEqual(first, REVIEW_REQUIRED)

        # Reopen the same database from a fresh Python process.
        public_keys = {
            key_id: {
                "source_id": config["source_id"],
                "public_key": config["public_key"].hex(),
            }
            for key_id, config in self.trusted.items()
        }

        input_data = {
            "record": self.record,
            "database": self.database,
            "trusted": public_keys,
            "digest": self.digest,
            "challenge": self.challenge,
        }

        child_code = """
import json
import sys
from verification_v3_1 import verify_once

data = json.load(sys.stdin)
trusted = {
    key_id: {
        "source_id": config["source_id"],
        "public_key": bytes.fromhex(config["public_key"]),
    }
    for key_id, config in data["trusted"].items()
}
result = verify_once(
    data["record"],
    database_path=data["database"],
    trusted_keys=trusted,
    expected_sha256=data["digest"],
    expected_challenge=data["challenge"],
)
print(result)
"""

        env = os.environ.copy()
        source_directory = str(Path(__file__).resolve().parent)
        env["PYTHONPATH"] = (
            source_directory
            + os.pathsep
            + env.get("PYTHONPATH", "")
        )

        child = subprocess.run(
            [sys.executable, "-c", child_code],
            input=json.dumps(input_data),
            text=True,
            capture_output=True,
            timeout=15,
            env=env,
            check=True,
        )

        self.assertEqual(child.stdout.strip(), HOLD)


if __name__ == "__main__":
    unittest.main()
