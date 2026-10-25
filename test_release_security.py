"""Offline release regressions using synthetic observations and test keys."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

from maniac.chain import run_chain
from maniac.evidence import HOLD, check_evidence
from maniac.simulation import Scenario
from shai_v31_bridge import evaluate
import test_maniac_evidence as evidence_tests
import test_shai_v31_bridge as bridge_tests


class TestEvidenceBoundaries(unittest.TestCase):
    def test_nonfinite_consent_expiry_holds(self):
        for value in (float('nan'), float('inf'), -float('inf'), True, 10 ** 400):
            with self.subTest(value=value):
                bundle = evidence_tests.good_bundle()
                bundle['consent']['expires_at'] = value
                result = check_evidence(bundle, evidence_tests.clock,
                                        provenance_checker=evidence_tests.fake_ok)
                self.assertEqual(result.overall, HOLD)
                self.assertFalse(result.approval_granted)
                self.assertTrue(any('consent expired' in reason for _, reason in result.reasons))

    def test_invalid_clock_holds_before_consuming_evidence(self):
        for value in (float('nan'), float('inf'), -float('inf'), True, None, 10 ** 400):
            with self.subTest(value=value):
                checker = Mock(return_value='REVIEW_REQUIRED')
                result = check_evidence(evidence_tests.good_bundle(), lambda: value,
                                        provenance_checker=checker)
                self.assertEqual(result.overall, HOLD)
                checker.assert_not_called()

    def test_invalid_numeric_policy_holds(self):
        for parameter in ('max_age', 'tolerance'):
            for value in (float('nan'), float('inf'), -float('inf'), True, -1, 10 ** 400):
                with self.subTest(parameter=parameter, value=value):
                    checker = Mock(return_value='REVIEW_REQUIRED')
                    result = check_evidence(evidence_tests.good_bundle(), evidence_tests.clock,
                                            provenance_checker=checker, **{parameter: value})
                    self.assertEqual(result.overall, HOLD)
                    checker.assert_not_called()

    def test_full_chain_nonfinite_consent_cannot_request_review(self):
        with tempfile.TemporaryDirectory() as folder:
            scenario = Scenario('release-consent', str(Path(folder) / 'replay.sqlite'))
            scenario.bundle['consent']['expires_at'] = float('nan')
            result = run_chain(scenario.supervisor, scenario.request, scenario.monitor,
                               scenario.bundle, scenario.clock)
            self.assertEqual(result.decision, HOLD)
            self.assertFalse(result.approval_granted)


class TestReplayStorageBoundaries(unittest.TestCase):
    def setUp(self):
        bridge_tests.BridgeTests.setUp(self)

    def test_transient_or_uri_replay_stores_hold(self):
        for path in (':memory:', Path(':memory:'), 'file::memory:?cache=shared', 'file:replay.sqlite'):
            with self.subTest(path=path):
                self.assertEqual(evaluate(self.envelope, db_path=path), HOLD)
                self.assertEqual(evaluate(self.envelope, db_path=path), HOLD)

    def test_invalid_replay_schema_holds(self):
        schemas = (
            'CREATE TABLE used_challenges (challenge TEXT)',
            'CREATE TABLE used_challenges (challenge INTEGER PRIMARY KEY)',
            'CREATE TABLE used_challenges (other TEXT PRIMARY KEY)',
            'CREATE TABLE used_challenges (challenge TEXT PRIMARY KEY, extra TEXT)',
        )
        for i, schema in enumerate(schemas):
            with self.subTest(schema=schema):
                path = Path(self.tmp.name) / ('schema-%d.sqlite' % i)
                conn = sqlite3.connect(path)
                try:
                    conn.execute(schema)
                    conn.commit()
                finally:
                    conn.close()
                self.assertEqual(evaluate(self.envelope, db_path=path), HOLD)
                self.assertEqual(evaluate(self.envelope, db_path=path), HOLD)

    def test_unconfirmed_insert_holds(self):
        triggers = (
            'CREATE TRIGGER ignore_insert BEFORE INSERT ON used_challenges '
            'BEGIN SELECT RAISE(IGNORE); END',
            'CREATE TRIGGER remove_insert AFTER INSERT ON used_challenges '
            'BEGIN DELETE FROM used_challenges WHERE challenge = NEW.challenge; END',
        )
        for i, trigger in enumerate(triggers):
            with self.subTest(trigger=i):
                path = Path(self.tmp.name) / ('trigger-%d.sqlite' % i)
                conn = sqlite3.connect(path)
                try:
                    conn.execute('CREATE TABLE used_challenges (challenge TEXT PRIMARY KEY)')
                    conn.execute(trigger)
                    conn.commit()
                finally:
                    conn.close()
                self.assertEqual(evaluate(self.envelope, db_path=path), HOLD)

    def test_valid_file_still_enforces_persistent_replay(self):
        self.assertEqual(evaluate(self.envelope, db_path=self.db), 'REVIEW_REQUIRED')
        self.assertEqual(evaluate(self.envelope, db_path=self.db), HOLD)


class TestBridgeInputBoundaries(unittest.TestCase):
    def test_deeply_nested_json_returns_hold_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.json'
            path.write_text('[' * 20000 + '0' + ']' * 20000)
            child = subprocess.run(
                [sys.executable, 'shai_v31_bridge.py', '--input', str(path),
                 '--replay-db', str(Path(folder) / 'replay.sqlite')],
                capture_output=True, text=True, timeout=15,
                cwd=Path(__file__).resolve().parent,
            )
            self.assertEqual(child.returncode, 2)
            self.assertEqual(json.loads(child.stdout), {'decision': HOLD, 'approval_granted': False})
            self.assertEqual(child.stderr, '')


if __name__ == '__main__':
    unittest.main()
