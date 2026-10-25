"""Review fixes (LOW): decision tamper-evidence, audit tail truncation, Doctor Review invariants."""
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

import test_maniac_verify as tmv
from maniac.audit import AuditChain, AuditError
from maniac.balance import close_loop, BALANCED, UNBALANCED
from maniac.verify import HUMAN_REVIEW, HumanDecision, decision_intact
from synth_shai_doctor.core import Review


class TestDecisionTamperEvident(unittest.TestCase):
    def genuine(self):
        res = tmv.consequence_review(**tmv.layers())
        rec = res.record_human_decision("mitch", "APPROVED", "ok")
        return res, rec

    def test_untouched_decision_balances(self):
        res, rec = self.genuine()
        self.assertTrue(decision_intact(res))
        b = close_loop(HUMAN_REVIEW, [], AuditChain(), human_decision=rec, verify_result=res)
        self.assertEqual(b.status, BALANCED)

    def test_probe_reset_then_rerecord_is_refused(self):
        res, _ = self.genuine()
        object.__setattr__(res, "human_decision", None)
        self.assertFalse(decision_intact(res))
        with self.assertRaises(ValueError):
            res.record_human_decision("x", "REJECTED", "y")

    def test_forced_overwrite_holds(self):
        res, _ = self.genuine()
        swapped = HumanDecision("intruder", "APPROVED", "forced")
        object.__setattr__(res, "human_decision", swapped)
        b = close_loop(HUMAN_REVIEW, [], AuditChain(), human_decision=swapped, verify_result=res)
        self.assertEqual((b.status, b.outcome), (UNBALANCED, "144 HOLD"))

    def test_field_edit_inside_record_holds(self):
        res, rec = self.genuine()
        object.__setattr__(rec, "operator_id", "someone-else")
        b = close_loop(HUMAN_REVIEW, [], AuditChain(), human_decision=rec, verify_result=res)
        self.assertEqual(b.status, UNBALANCED)


class TestAuditTailTruncation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "a.sqlite")

    def sql(self, statement):
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute(statement)

    def test_probe_tail_delete_detected_without_expected_head(self):
        c = AuditChain(self.path); c.append("g", "o"); c.append("g2", "o2")
        self.sql("DELETE FROM audit_entries WHERE position=1")
        with self.assertRaises(AuditError):
            AuditChain(self.path)

    def test_intact_store_reopens_and_appends(self):
        c = AuditChain(self.path); c.append("g", "o")
        d = AuditChain(self.path); d.append("g2", "o2")
        self.assertEqual(len(AuditChain(self.path).entries), 2)

    def test_pre_anchor_database_is_adopted(self):
        c = AuditChain(self.path); c.append("g", "o")
        self.sql("DROP TABLE audit_anchor")               # simulate an older database
        d = AuditChain(self.path)                          # backwards compatible: anchored now
        self.assertEqual(len(d.entries), 1)
        d.append("g2", "o2")
        self.sql("DELETE FROM audit_entries WHERE position=1")
        with self.assertRaises(AuditError):
            AuditChain(self.path)

    def test_run_loop_holds_on_truncated_store(self):
        import test_maniac_loop as tml
        from maniac.loop import run_loop
        from maniac.triangulate import readings_from_bundle
        c = AuditChain(self.path); c.append("g", "o"); c.append("g2", "o2")
        self.sql("DELETE FROM audit_entries WHERE position=1")
        s = tml.Scenario("trunc", os.path.join(self.tmp.name, "replay.sqlite"))
        r, _ = run_loop(s.supervisor, s.request, s.monitor, s.bundle, s.clock, expected_value=10.1,
                        fresh_readings=readings_from_bundle(s.bundle), audit_path=self.path)
        self.assertEqual((r.status, r.outcome), (UNBALANCED, "144 HOLD"))


class TestDoctorReviewInvariants(unittest.TestCase):
    def test_probe_human_approval_not_required_rejected(self):
        with self.assertRaises(ValueError):
            Review("v", "SYNTHETIC-1", "REVIEW", (), "", human_approval_required=False)

    def test_other_unsafe_flags_rejected(self):
        for kw in ({"human_approval_required": 1}, {"human_approval_required": None},
                   {"diagnosis_made": True}, {"autonomous_dispatch": True}, {"diagnosis_made": 0}):
            with self.subTest(kw=kw):
                with self.assertRaises(ValueError):
                    Review("v", "SYNTHETIC-1", "REVIEW", (), "", **kw)

    def test_default_review_is_safe(self):
        r = Review("v", "SYNTHETIC-1", "REVIEW", (), "")
        self.assertIs(r.human_approval_required, True)


if __name__ == "__main__":
    unittest.main()
