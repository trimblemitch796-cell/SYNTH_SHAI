"""Offline concurrency and replay checks for the V3.1 SQLite evidence gate."""
import concurrent.futures
import sqlite3
from contextlib import closing
import unittest
import test_verification_v3_1 as v31_tests  # module import, so discover does not run those 15 tests twice
from verification_v3_1 import HOLD, REVIEW_REQUIRED, verify_once


class ConcurrentReplayTests(unittest.TestCase):
    def setUp(self):
        v31_tests.CatharsisV31Tests.setUp(self)

    def evaluate(self):
        return verify_once(self.record, database_path=self.database, **self.arguments)

    def test_concurrent_duplicate_challenge_one_review_only(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(lambda _: self.evaluate(), range(12)))
        self.assertEqual(outcomes.count(REVIEW_REQUIRED), 1, outcomes)
        self.assertEqual(outcomes.count(HOLD), 11, outcomes)

    def test_repeated_concurrent_attempts_cannot_reopen_gate(self):
        self.assertEqual(self.evaluate(), REVIEW_REQUIRED)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(lambda _: self.evaluate(), range(12)))
        self.assertEqual(outcomes, [HOLD] * 12)

    def test_replay_after_new_connection_stays_hold(self):
        self.assertEqual(self.evaluate(), REVIEW_REQUIRED)
        with closing(sqlite3.connect(self.database)) as db, db:
            count = db.execute("SELECT COUNT(*) FROM used_challenges").fetchone()[0]
        self.assertEqual(count, 1)
        self.assertEqual(self.evaluate(), HOLD)

    def test_corrupt_database_fails_closed(self):
        with open(self.database, "wb") as handle:
            handle.write(b"not an sqlite database")
        self.assertEqual(self.evaluate(), HOLD)


if __name__ == "__main__":
    unittest.main()
