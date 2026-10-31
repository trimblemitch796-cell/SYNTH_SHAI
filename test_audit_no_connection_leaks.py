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
from unittest.mock import patch

from maniac.audit import AuditChain, AuditError


def _sqlite_emits_resource_warning():
    """Feature-detect: does this Python warn when an unclosed sqlite3 connection is
    collected? (CPython 3.13+ does; earlier versions do not, so the guard cannot
    see leaks there and only the 3.13+ runs are meaningful.)"""
    gc.collect()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        conn = sqlite3.connect(":memory:")
        del conn
        gc.collect()
    return any(issubclass(w.category, ResourceWarning) for w in caught)


SQLITE_WARNS = _sqlite_emits_resource_warning()
# CI's Python 3.13 job sets this, so the guard can never silently skip there.
REQUIRE_GUARD = os.environ.get("SHAI_REQUIRE_LEAK_GUARD") == "1"


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
        if SQLITE_WARNS:
            # CPython 3.13+ provides an actual sqlite3 leak signal.
            def leak():
                conn = sqlite3.connect(self.path)
                conn.execute("SELECT 1")
                del conn
            self.assertTrue(self.leaks(leak), "leak detector is not working")
        else:
            # Python 3.11 cannot emit the sqlite3 ResourceWarning. Instead,
            # instrument the audit's own connection lifecycle directly and
            # assert every acquired connection receives close(), including
            # after an error. Do NOT pretend this is a warning-based detector.
            acquired = []
            original = AuditChain._connect

            class TrackingConnection:
                def __init__(self, conn):
                    self.conn = conn
                    self.closed = False

                def __getattr__(self, attr):
                    return getattr(self.conn, attr)

                def __enter__(self):
                    self.conn.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.conn.__exit__(*args)

                def close(self):
                    self.closed = True
                    self.conn.close()

            def tracked(chain):
                wrapper = TrackingConnection(original(chain))
                acquired.append(wrapper)
                return wrapper

            with patch.object(AuditChain, "_connect", tracked):
                chain = AuditChain(self.path)
                chain.append("GATE", "OK", "test")
                with self.assertRaises(AuditError):
                    AuditChain(self.path, expected_head="0" * 64)
            self.assertGreaterEqual(len(acquired), 3)
            self.assertTrue(all(x.closed for x in acquired),
                            "audit did not close all instrumented connections")

    def test_guard_active_when_required(self):
        if REQUIRE_GUARD:
            self.assertTrue(SQLITE_WARNS, "SHAI_REQUIRE_LEAK_GUARD=1 but this Python does not emit "
                                          "sqlite ResourceWarnings, so the leak guard would be blind")

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
