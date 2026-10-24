"""Adversarial offline tests for SYNTH_SHAI V3.1 bridge."""
import copy
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from verification_v3 import canonical_bytes, sha256_text, HOLD, REVIEW_REQUIRED
from shai_v31_bridge import evaluate


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'replay.sqlite'
        report = 'Offline only: no actuation'
        revision = 'v31-test'
        challenge = 'synthetic-challenge-987654321'
        digest = sha256_text(report)
        trusted = {}
        evidence = []
        for i in range(2):
            private = Ed25519PrivateKey.generate()
            public = private.public_key().public_bytes(
                encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
            source, key = f'source-{i}', f'key-{i}'
            trusted[key] = {'source_id': source, 'public_key_hex': public.hex()}
            item = {'source_id': source, 'key_id': key, 'source_revision': revision,
                    'report_sha256': digest, 'challenge': challenge}
            evidence.append({**item, 'signature': private.sign(canonical_bytes(item)).hex()})
        self.envelope = {'record': {'test_report': report, 'source_revision': revision,
                                    'challenge': challenge, 'verification_evidence': evidence},
                         'trusted_keys': trusted, 'expected_sha256': digest,
                         'expected_challenge': challenge}

    def check(self, envelope):
        return evaluate(envelope, db_path=self.db)

    def test_valid_evidence_requests_review_not_approval(self):
        self.assertEqual(self.check(self.envelope), REVIEW_REQUIRED)

    def test_replay_holds(self):
        self.assertEqual(self.check(self.envelope), REVIEW_REQUIRED)
        self.assertEqual(self.check(self.envelope), HOLD)

    def test_tampered_report_holds(self):
        value = copy.deepcopy(self.envelope)
        value['record']['test_report'] += ' altered'
        self.assertEqual(self.check(value), HOLD)

    def test_forged_signature_holds(self):
        value = copy.deepcopy(self.envelope)
        value['record']['verification_evidence'][0]['signature'] = '00' * 64
        self.assertEqual(self.check(value), HOLD)

    def test_missing_trusted_key_holds(self):
        value = copy.deepcopy(self.envelope)
        del value['trusted_keys']['key-1']
        self.assertEqual(self.check(value), HOLD)

    def test_operator_pressure_cannot_override(self):
        value = copy.deepcopy(self.envelope)
        value['urgent_override'] = True
        self.assertEqual(self.check(value), HOLD)

    def test_invalid_key_encoding_holds(self):
        value = copy.deepcopy(self.envelope)
        value['trusted_keys']['key-0']['public_key_hex'] = 'not a key'
        self.assertEqual(self.check(value), HOLD)

    def test_missing_input_holds(self):
        self.assertEqual(self.check({}), HOLD)

    def test_recovery_fresh_challenge_after_hold(self):
        bad = copy.deepcopy(self.envelope)
        bad['record']['test_report'] = 'tampered'
        self.assertEqual(self.check(bad), HOLD)
        self.assertEqual(self.check(self.envelope), REVIEW_REQUIRED)

    def test_corrupt_database_fails_closed(self):
        self.db.write_bytes(b'not-sqlite')
        self.assertEqual(self.check(self.envelope), HOLD)


if __name__ == '__main__':
    unittest.main()
