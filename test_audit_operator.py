"""Review fix (MEDIUM): the audit records WHO approved (offline simulation only)."""
import json
import os
import sqlite3
import unittest

import test_maniac_loop as tml
from maniac.audit import AuditChain, verify_chain
from maniac.balance import BALANCED, UNBALANCED
from maniac.loop import run_loop
from maniac.triangulate import readings_from_bundle


class TestAuditRecordsOperator(tml.Base):
    def run_it(self, s, **kw):
        return run_loop(s.supervisor, s.request, s.monitor, s.bundle, s.clock,
                        expected_value=10.1, fresh_readings=readings_from_bundle(s.bundle), **kw)

    def human_entry(self, chain):
        return [e for e in chain.entries if e["gate"] == "HUMAN REVIEW"][0]

    def test_operator_and_plan_digest_in_audit(self):
        r, chain = self.run_it(self.scenario("op"), human=("mitch", "APPROVED", "checked"),
                               plan_sha256="ab" * 32)
        self.assertEqual(r.status, BALANCED)
        detail = json.loads(self.human_entry(chain)["detail"])
        self.assertEqual(detail, {"operator_id": "mitch", "reason": "checked", "plan_sha256": "ab" * 32})
        self.assertTrue(verify_chain(chain.entries))

    def test_operator_in_sqlite_audit_and_chain_reloads(self):
        path = os.path.join(self.tmp.name, "audit.sqlite")
        r, chain = self.run_it(self.scenario("sq"), human=("op-7", "APPROVED", "ok"), audit_path=path)
        self.assertEqual(r.status, BALANCED)
        with sqlite3.connect(path) as conn:
            rows = [json.loads(p) for (p,) in conn.execute("SELECT payload FROM audit_entries")]
        human = [e for e in rows if e["gate"] == "HUMAN REVIEW"][0]
        self.assertEqual(json.loads(human["detail"])["operator_id"], "op-7")
        reloaded = AuditChain(path, expected_head=chain.head)   # verifies on load
        self.assertEqual(reloaded.entries, chain.entries)

    def test_missing_or_empty_operator_holds_and_is_not_logged_as_decision(self):
        for i, op in enumerate(("", "   ", None, True)):
            with self.subTest(op=op):
                r, chain = self.run_it(self.scenario("missing-op-%d" % i), human=(op, "APPROVED", "x"))
                self.assertEqual((r.status, r.outcome), (UNBALANCED, "144 HOLD"))
                self.assertIsNone(r.human_decision)
                self.assertEqual(self.human_entry(chain)["outcome"], "refused")
                self.assertTrue(verify_chain(chain.entries))

    def test_old_style_detail_still_verifies(self):
        c = AuditChain()
        c.append("HUMAN REVIEW", "APPROVED", "plain reason text (pre-fix format)")
        self.assertTrue(verify_chain(c.entries))

    def test_twin_motion_audit_has_operator_and_plan(self):
        import test_shai_twin as tst
        from shai.twin import approval_for, plan_digest, MOVED
        t = tst.ShaiTwin(replay_db=os.path.join(self.tmp.name, "replay.sqlite"))
        plan = {"request_id": "r1", "moves": {"elbow_left": 30}, "duration_s": 2.0}
        from maniac.simulation import signed_envelope
        captured = {}
        import maniac.loop as loop_mod
        real = loop_mod.human_review_detail
        def spy(rec, digest=None):
            captured["detail"] = real(rec, digest)
            return captured["detail"]
        loop_mod.human_review_detail = spy
        try:
            r = t.request_motion(plan, approval_for(plan, "mitch", "APPROVED", "ok"),
                                 {"envelope": signed_envelope("audit-op-twin-%s" % id(self))}, tst.GOOD)
        finally:
            loop_mod.human_review_detail = real
        self.assertEqual(r.outcome, MOVED)
        d = json.loads(captured["detail"])
        self.assertEqual((d["operator_id"], d["plan_sha256"]), ("mitch", plan_digest(plan)))


if __name__ == "__main__":
    unittest.main()
