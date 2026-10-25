"""Durable audit tests use synthetic local data only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from maniac.audit import AuditChain, AuditError, GENESIS, verify_chain


class TestDurableAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "audit.sqlite"

    def execute(self, sql, parameters=()):
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute(sql, parameters)

    def test_restart_loads_and_continues_identical_hashes(self):
        memory = AuditChain()
        stored = AuditChain(self.path)
        for chain in (memory, stored):
            chain.append("444000", "HUMAN_REVIEW", "synthetic evidence")
            chain.append("999000", "intact")
        resumed = AuditChain(self.path, expected_head=stored.head)
        self.assertEqual(resumed.entries, memory.entries)
        expected = memory.append("BALANCE", "BALANCED")
        self.assertEqual(resumed.append("BALANCE", "BALANCED"), expected)
        self.assertEqual(AuditChain(self.path).head, expected)

    def test_edit_is_refused_on_load_and_append(self):
        chain = AuditChain(self.path)
        chain.append("444000", "HUMAN_REVIEW")
        entry = dict(chain.entries[0], outcome="edited")
        self.execute("UPDATE audit_entries SET payload = ?", (json.dumps(entry),))
        with self.assertRaises(AuditError):
            AuditChain(self.path)
        with self.assertRaises(AuditError):
            chain.append("999000", "intact")
        self.assertEqual(len(chain.entries), 1)

    def test_malformed_json_and_partial_entry_are_refused(self):
        chain = AuditChain(self.path)
        chain.append("444000", "HUMAN_REVIEW")
        for payload in ("{", "{}", "null", "[]", "[" * 20000 + "0" + "]" * 20000):
            with self.subTest(payload=payload):
                self.execute("UPDATE audit_entries SET payload = ?", (payload,))
                with self.assertRaises(AuditError):
                    AuditChain(self.path)

    def test_deleting_middle_entry_is_detected(self):
        chain = AuditChain(self.path)
        for _ in range(3):
            chain.append("gate", "ok")
        self.execute("DELETE FROM audit_entries WHERE position = 1")
        with self.assertRaises(AuditError):
            AuditChain(self.path)

    def test_suffix_deletion_needs_external_checkpoint(self):
        chain = AuditChain(self.path)
        chain.append("first", "ok")
        prefix_head = chain.head
        chain.append("second", "ok")
        checkpoint = chain.head
        self.execute("DELETE FROM audit_entries WHERE position = 1")
        with self.assertRaises(AuditError):          # stored anchor catches tail deletion
            AuditChain(self.path)
        with self.assertRaises(AuditError):
            AuditChain(self.path, expected_head=checkpoint)
        # An attacker who also deletes the anchor is only caught by the external checkpoint
        self.execute("DELETE FROM audit_anchor")
        self.assertEqual(AuditChain(self.path).head, prefix_head)
        self.execute("DELETE FROM audit_entries")
        self.execute("DELETE FROM audit_anchor")
        self.assertEqual(AuditChain(self.path).head, GENESIS)
        with self.assertRaises(AuditError):
            AuditChain(self.path, expected_head=checkpoint)

    def test_stale_writer_must_reload_without_losing_entries(self):
        first = AuditChain(self.path)
        stale = AuditChain(self.path)
        first.append("first", "ok")
        with self.assertRaises(AuditError):
            stale.append("stale", "ok")
        self.assertEqual(stale.entries, [])
        resumed = AuditChain(self.path)
        resumed.append("second", "ok")
        self.assertEqual([e["gate"] for e in resumed.entries], ["first", "second"])

    def test_concurrent_writers_cannot_fork_log(self):
        writers = [AuditChain(self.path), AuditChain(self.path)]
        barrier = threading.Barrier(2)

        def append(chain):
            barrier.wait()
            try:
                chain.append("gate", "ok")
                return True
            except AuditError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(append, writers))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(len(AuditChain(self.path).entries), 1)

    def test_failed_insert_leaves_memory_and_storage_unchanged(self):
        chain = AuditChain(self.path)
        chain.append("first", "ok")
        checkpoint = chain.head
        self.execute("CREATE TRIGGER refuse_append BEFORE INSERT ON audit_entries "
                     "BEGIN SELECT RAISE(ABORT, 'synthetic write failure'); END")
        with self.assertRaises(AuditError):
            chain.append("second", "ok")
        self.assertEqual(chain.head, checkpoint)
        self.assertEqual(AuditChain(self.path, expected_head=checkpoint).entries, chain.entries)

    def test_storage_unavailable_is_an_error_not_empty_history(self):
        with self.assertRaises(AuditError):
            AuditChain(Path(self.temp.name) / "missing" / "audit.sqlite")
        chain = AuditChain(self.path)
        with patch.object(chain, "_connect", side_effect=sqlite3.OperationalError("offline failure")):
            with self.assertRaises(AuditError):
                chain.append("gate", "ok")
        self.assertEqual(chain.entries, [])
        self.assertEqual(AuditChain(self.path).entries, [])

    def test_invalid_sqlite_file_is_not_overwritten(self):
        original = b"synthetic damaged database"
        self.path.write_bytes(original)
        with self.assertRaises(AuditError):
            AuditChain(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_persistence_requires_file_path(self):
        for path in ("", ":memory:"):
            with self.subTest(path=path), self.assertRaises(AuditError):
                AuditChain(path)

    def test_checkpoint_and_strict_index_validation(self):
        chain = AuditChain()
        chain.append("gate", "ok")
        self.assertTrue(verify_chain(chain.entries, chain.head))
        self.assertFalse(verify_chain(chain.entries, GENESIS))
        self.assertFalse(verify_chain([], chain.head))
        self.assertTrue(verify_chain([], GENESIS))
        chain.entries[0]["index"] = False
        self.assertFalse(verify_chain(chain.entries))


if __name__ == "__main__":
    unittest.main()
