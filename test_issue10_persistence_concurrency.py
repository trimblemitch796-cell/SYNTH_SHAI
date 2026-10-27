"""Issue #10: offline failure-oriented checks for SQLite replay and evidence trust.

This tests same-host durability and documents trust limits. No real secrets or users.
"""
import concurrent.futures
import copy
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

from test_verification_v3_1 import CatharsisV31Tests
from verification_v3_1 import HOLD, REVIEW_REQUIRED, verify_once, verify_result


class Issue10PersistenceAndConcurrency(CatharsisV31Tests):
    def test_simultaneous_identical_challenge_single_review(self):
        def attempt(_):
            return verify_once(self.record, database_path=self.database, **self.arguments)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(16)))
        self.assertEqual(results.count(REVIEW_REQUIRED), 1)
        self.assertEqual(results.count(HOLD), 15)

    def test_broken_sqlite_file_holds(self):
        Path(self.database).write_bytes(b"not-a-sqlite-database")
        self.assertEqual(
            verify_once(self.record, database_path=self.database, **self.arguments), HOLD
        )

    def test_read_only_database_holds_when_challenge_new(self):
        # Use a SQLite URI? Deliberately do not: verifier explicitly rejects URI paths.
        self.assertEqual(
            verify_once(self.record, database_path="file:ro?mode=ro", **self.arguments), HOLD
        )

    def test_incompatible_replay_schema_holds(self):
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("CREATE TABLE used_challenges (challenge TEXT, extra TEXT)")
        self.assertEqual(
            verify_once(self.record, database_path=self.database, **self.arguments), HOLD
        )

    def test_replay_after_database_reopen_holds(self):
        self.assertEqual(verify_once(self.record, database_path=self.database, **self.arguments), REVIEW_REQUIRED)
        self.assertEqual(verify_once(self.record, database_path=self.database, **self.arguments), HOLD)

    def test_substituted_source_identity_holds(self):
        modified = copy.deepcopy(self.record)
        modified["verification_evidence"][0]["source_id"] = "untrusted-other-source"
        self.assertEqual(verify_result(modified, **self.arguments), HOLD)

    def test_caller_supplied_trusted_keys_are_not_attestation(self):
        # Valid signed evidence only reaches human review, never grants approval.
        self.assertEqual(verify_result(self.record, **self.arguments), REVIEW_REQUIRED)


if __name__ == "__main__":
    unittest.main()
