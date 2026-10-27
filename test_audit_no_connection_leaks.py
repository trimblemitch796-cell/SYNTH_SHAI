"""Regression: maniac/audit.py must close every SQLite connection deterministically.
Runs audit operations (create, append, reload, checkpoint mismatch, tamper, storage
failure) while recording ResourceWarnings, forces gc, and fails on any leak."""
import gc
import os
import sqlite3
import tempfile
import unittest
import warnings
from contextlib import closing

from maniac.audit import AuditChain, AuditError


class AuditConnectionLeakTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "audit.sqlite")

    def leaks(self, fn):
        gc.collect()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            fn()
            gc.collect()
        return [w for w in caught if issubclass(w.category, ResourceWarning)]

    def test_detector_catches_a_deliberate_leak(self):
        def leak():
            conn = sqlite3.connect(self.path)
            conn.execute("SELECT 1")
            del conn
        self.assertTrue(self.leaks(leak), "leak detector is not working")

    def test_audit_operations_do_not_leak(self):
        def ops():
            chain = AuditChain(self.path)
            for i in range(3):
                chain.append("GATE", "OK", "detail %d" % i)
            head = chain.head
            AuditChain(self.path, expected_head=head)              # reload + verify
            with self.assertRaises(AuditError):
                AuditChain(self.path, expected_head="0" * 64)      # checkpoint mismatch
            stale = AuditChain(self.path)
            chain.append("GATE", "OK", "moves on")
            with self.assertRaises(AuditError):
                stale.append("GATE", "OK", "stale")                # changed under us
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute("UPDATE audit_entries SET payload = '{}' WHERE position = 0")
            with self.assertRaises(AuditError):
                AuditChain(self.path)                               # tampered
            with self.assertRaises(AuditError):
                AuditChain(os.path.join(self.tmp.name, "missing", "dir", "a.sqlite"))  # storage error
            AuditChain().append("MEM", "OK")                        # in-memory chain
        self.assertEqual(self.leaks(ops), [])


if __name__ == "__main__":
    unittest.main()
