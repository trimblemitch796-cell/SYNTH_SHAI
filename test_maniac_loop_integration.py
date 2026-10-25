"""Offline loop regressions for safeguarding and durable audit composition."""
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from maniac.audit import AuditChain, AuditError, verify_chain
from maniac.learn import LessonLog
from maniac.loop import run_loop
from maniac.triangulate import readings_from_bundle
from test_maniac_loop import Base, GOOD_NOTE
from v25_tri5 import SafetySignals

CLEAR = SafetySignals("unknown", False, False, False, True)
APPROVAL = ("operator", "APPROVED", "synthetic review")


class TestLoopIntegration(Base):
    def loop(self, scenario=None, **kwargs):
        s = scenario if scenario is not None else self.scenario()
        kwargs.setdefault("expected_value", 10.1)
        kwargs.setdefault("fresh_readings", readings_from_bundle(s.bundle))
        return run_loop(s.supervisor, s.request, s.monitor, s.bundle, s.clock, **kwargs)

    def test_optional_safeguarding_preserves_existing_scope(self):
        result, _ = self.loop()
        self.assertEqual(result.status, "BALANCED")
        self.assertIsNone(result.safety_decision)
        self.assertFalse(result.approval_granted)

    def test_clear_safeguarding_runs_before_recording_human_choice(self):
        result, chain = self.loop(safety_signals=CLEAR, human=APPROVAL)
        self.assertEqual(result.status, "BALANCED")
        self.assertTrue(result.human_decision.approved)
        self.assertEqual(result.safety_decision.outcome, "HUMAN_REVIEW")
        gates = [entry["gate"] for entry in chain.entries]
        self.assertLess(gates.index("V25 TRI5"), gates.index("HUMAN REVIEW"))
        self.assertFalse(result.approval_granted)

    def test_explicit_missing_or_malformed_signals_hold(self):
        for i, signals in enumerate((None, {}, True, replace(CLEAR, privacy_risk="False"))):
            with self.subTest(signals=signals):
                result, _ = self.loop(self.scenario(str(i)), safety_signals=signals,
                                      human=APPROVAL)
                self.assertEqual(result.outcome, "144 HOLD")
                self.assertIsNone(result.human_decision)

    def test_missing_reviewer_vetoes_human_choice(self):
        log = LessonLog()
        result, chain = self.loop(safety_signals=replace(CLEAR, qualified_reviewer_available=False),
                                  human=APPROVAL, lessons=log)
        self.assertEqual(result.status, "UNBALANCED")
        self.assertIsNone(result.human_decision)
        self.assertNotIn("HUMAN REVIEW", [entry["gate"] for entry in chain.entries])
        self.assertIn('"outcome": "144 HOLD"', log.lines()[0])

    def test_urgent_advice_holds_without_recording_approval(self):
        result, chain = self.loop(safety_signals=replace(CLEAR, immediate_danger=True),
                                  human=APPROVAL)
        self.assertEqual(result.outcome, "144 HOLD")
        self.assertEqual(result.safety_decision.outcome, "URGENT_HUMAN_HELP")
        self.assertIsNone(result.human_decision)
        self.assertTrue(any(e["outcome"] == "URGENT_HUMAN_HELP" for e in chain.entries))

    def test_upstream_hold_retains_urgent_advice(self):
        s = self.scenario()
        s.bundle["action"] = "unapproved"
        result, _ = self.loop(s, safety_signals=replace(CLEAR, immediate_danger=True),
                              human=APPROVAL)
        self.assertEqual(result.outcome, "144 HOLD")
        self.assertEqual(result.safety_decision.outcome, "URGENT_HUMAN_HELP")
        self.assertIsNone(result.human_decision)

    def test_clear_safeguarding_does_not_override_upstream_hold(self):
        s = self.scenario()
        s.bundle["action"] = "unapproved"
        result, _ = self.loop(s, safety_signals=CLEAR, human=APPROVAL)
        self.assertEqual(result.outcome, "144 HOLD")
        self.assertIsNone(result.human_decision)

    def test_review_flags_remain_advisory(self):
        for flag in ("privacy_risk", "suspected_exploitation"):
            with self.subTest(flag=flag):
                result, _ = self.loop(self.scenario(flag),
                                      safety_signals=replace(CLEAR, **{flag: True}))
                self.assertEqual(result.outcome, "HUMAN_REVIEW")
                self.assertIn("qualified human review", result.safety_decision.reason)
                self.assertFalse(result.approval_granted)

    def test_recovery_cannot_skip_safeguarding_veto(self):
        s = self.scenario()
        held, request, bundle = self.held_then_fresh(s)
        s.bundle = held
        result, _ = self.loop(s, fresh_readings=readings_from_bundle(bundle),
                              recovery={"repair_note": GOOD_NOTE, "request": request, "bundle": bundle},
                              safety_signals=replace(CLEAR, qualified_reviewer_available=False),
                              human=APPROVAL)
        self.assertEqual(result.outcome, "144 HOLD")
        self.assertIsNone(result.human_decision)

    def test_audit_survives_reopen_and_continues_next_loop(self):
        path = Path(self.tmp.name) / "audit.sqlite"
        first, chain = self.loop(self.scenario("first"), audit_path=path, safety_signals=CLEAR)
        saved = list(chain.entries)
        reopened = AuditChain(path, expected_head=first.audit_head)
        self.assertEqual(reopened.entries, saved)
        second, chain = self.loop(self.scenario("second"), audit_path=path,
                                  audit_expected_head=first.audit_head)
        self.assertEqual(chain.entries[:len(saved)], saved)
        self.assertTrue(verify_chain(chain.entries, expected_head=second.audit_head))
        self.assertEqual(AuditChain(path).head, second.audit_head)

    def test_corrupt_audit_holds_before_consuming_request(self):
        path = Path(self.tmp.name) / "audit.sqlite"
        path.write_bytes(b"not a database")
        s = self.scenario()
        with patch("maniac.loop.run_chain") as run_chain:
            result, chain = self.loop(s, audit_path=path)
        run_chain.assert_not_called()
        self.assertEqual(result.outcome, "144 HOLD")
        self.assertEqual(path.read_bytes(), b"not a database")
        self.assertTrue(verify_chain(chain.entries))

    def test_checkpoint_mismatch_holds(self):
        path = Path(self.tmp.name) / "audit.sqlite"
        first, _ = self.loop(self.scenario("first"), audit_path=path)
        result, _ = self.loop(self.scenario("second"), audit_path=path,
                              audit_expected_head="0" * 64)
        self.assertEqual(result.outcome, "144 HOLD")
        self.assertEqual(AuditChain(path).head, first.audit_head)

    def test_audit_failure_preserves_urgent_help_advice(self):
        result, _ = self.loop(audit_path=Path(self.tmp.name),
                              safety_signals=replace(CLEAR, immediate_danger=True),
                              human=APPROVAL)
        self.assertEqual(result.outcome, "144 HOLD")
        self.assertEqual(result.safety_decision.outcome, "URGENT_HUMAN_HELP")
        self.assertIsNone(result.human_decision)

    def test_malformed_audit_path_holds(self):
        for path in (123, "bad\x00path"):
            with self.subTest(path=path):
                result, _ = self.loop(audit_path=path)
                self.assertEqual(result.outcome, "144 HOLD")

    def test_persistence_failure_even_at_final_balance_holds(self):
        original = AuditChain.append

        # Failure trail is deliberately in-memory, so let its final HOLD append work.
        calls = 0

        def fail_once(chain, gate, *args, **kwargs):
            nonlocal calls
            if gate == "Δ BALANCE" and calls == 0:
                calls += 1
                raise AuditError("simulated disk failure")
            return original(chain, gate, *args, **kwargs)

        with patch.object(AuditChain, "append", fail_once):
            result, chain = self.loop(human=APPROVAL)
        self.assertEqual(result.status, "UNBALANCED")
        self.assertIsNone(result.human_decision)
        self.assertFalse(result.approval_granted)
        self.assertTrue(verify_chain(chain.entries))
