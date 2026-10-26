"""Adversarial offline tests for SYNTH_SHAI V3.1 bridge."""
import copy
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from verification_v3 import canonical_bytes, sha256_text, HOLD, REVIEW_REQUIRED
from shai_v31_bridge import evaluate, TrustConfig


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'replay.sqlite'
        self.report = 'Offline only: no actuation'
        self.digest = sha256_text(self.report)
        self.challenge = 'synthetic-challenge-987654321'
        self.private_keys = [Ed25519PrivateKey.generate() for _ in range(2)]
        trusted = {}
        for i, private in enumerate(self.private_keys):
            public = private.public_key().public_bytes(
                encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
            trusted[f'key-{i}'] = {'source_id': f'source-{i}', 'public_key_hex': public.hex()}
        # Trust material is held by the verifier, separate from the envelope.
        self.trusted = trusted
        self.trust = TrustConfig(trusted)
        self.envelope = BridgeTests.envelope_for(self, self.challenge)

    def envelope_for(self, challenge, private_keys=None):
        """Sign evidence over `challenge`. Returns {'record': ...} only."""
        revision, evidence = 'v31-test', []
        for i, private in enumerate(private_keys or self.private_keys):
            item = {'source_id': f'source-{i}', 'key_id': f'key-{i}', 'source_revision': revision,
                    'report_sha256': self.digest, 'challenge': challenge}
            evidence.append({**item, 'signature': private.sign(canonical_bytes(item)).hex()})
        return {'record': {'test_report': self.report, 'source_revision': revision,
                           'challenge': challenge, 'verification_evidence': evidence}}

    def bridge_kwargs(self, trust=None):
        return {'trust': trust or self.trust, 'expected_challenge': self.challenge,
                'expected_sha256': self.digest}

    def check(self, envelope, trust=None):
        return evaluate(envelope, db_path=self.db, **self.bridge_kwargs(trust))

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
        trusted = copy.deepcopy(self.trusted)
        del trusted['key-1']
        self.assertEqual(self.check(self.envelope, TrustConfig(trusted)), HOLD)

    def test_operator_pressure_cannot_override(self):
        value = copy.deepcopy(self.envelope)
        value['urgent_override'] = True
        self.assertEqual(self.check(value), HOLD)

    def test_invalid_key_encoding_holds(self):
        trusted = copy.deepcopy(self.trusted)
        trusted['key-0']['public_key_hex'] = 'not a key'
        self.assertEqual(self.check(self.envelope, TrustConfig(trusted)), HOLD)

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
