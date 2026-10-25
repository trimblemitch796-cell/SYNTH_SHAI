"""Issue #10: offline adversarial regressions for V3.1 verification.

All inputs are synthetic; no live accounts, keys, children or external systems.
"""
import copy
import tempfile
import unittest
from pathlib import Path

from test_verification_v3_1 import CatharsisV31Tests
from verification_v3_1 import HOLD, REVIEW_REQUIRED, verify_once, verify_result
from shai_v31_bridge import evaluate


class Issue10AdversarialTests(CatharsisV31Tests):
    def test_malformed_record_shapes_hold(self):
        for record in (None, [], (), 7, True, {}, {"test_report": "x"}):
            with self.subTest(record=repr(record)):
                self.assertEqual(self.check(record), HOLD)

    def test_invalid_signed_evidence_hold(self):
        for bad in (None, {}, "not-a-list", [], [self.entries[0]]):
            with self.subTest(value=repr(bad)):
                record = copy.deepcopy(self.record)
                record["verification_evidence"] = bad
                self.assertEqual(self.check(record), HOLD)

    def test_forged_signature_and_wrong_source_hold(self):
        for change in ("signature", "source_id", "challenge"):
            with self.subTest(change=change):
                record = copy.deepcopy(self.record)
                record["verification_evidence"][0][change] = (
                    "00" * 64 if change == "signature" else "fake-source"
                )
                self.assertEqual(self.check(record), HOLD)

    def test_replay_same_database_holds(self):
        first = verify_once(self.record, database_path=self.database, **self.arguments)
        second = verify_once(self.record, database_path=self.database, **self.arguments)
        self.assertEqual(first, REVIEW_REQUIRED)
        self.assertEqual(second, HOLD)

    def test_ephemeral_and_bad_database_paths_hold(self):
        for path in (None, "", ":memory:", "file:temporary?mode=memory"):
            with self.subTest(path=path):
                self.assertEqual(verify_once(self.record, database_path=path, **self.arguments), HOLD)

    def test_bridge_invalid_envelopes_hold(self):
        for value in (None, {}, [], "x", {"record": self.record}):
            with self.subTest(value=repr(value)):
                self.assertEqual(evaluate(value, db_path=self.database), HOLD)

    def test_no_approval_field_can_be_injected(self):
        modified = copy.deepcopy(self.record)
        modified["approval_granted"] = True
        self.assertEqual(self.check(modified), HOLD)

    def test_oversize_report_holds(self):
        modified = copy.deepcopy(self.record)
        modified["test_report"] = "X" * 1000001
        self.assertEqual(self.check(modified), HOLD)


if __name__ == "__main__":
    unittest.main()
