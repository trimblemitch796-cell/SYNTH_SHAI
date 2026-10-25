"""Δ BALANCE - close the loop (offline simulation only - no hardware).

BALANCED only when every gate in the loop completed cleanly AND the audit
chain verifies. Otherwise UNBALANCED, which always means 144 HOLD.
The result is frozen and never approves anything.
"""
from dataclasses import dataclass

from maniac.audit import verify_chain

GATE = "Δ BALANCE"
BALANCED = "BALANCED"
UNBALANCED = "UNBALANCED"
HOLD = "144 HOLD"
HUMAN_REVIEW = "HUMAN_REVIEW"


@dataclass(frozen=True)
class BalanceResult:
    outcome: str              # "HUMAN_REVIEW" or "144 HOLD"
    status: str               # "BALANCED" or "UNBALANCED"
    gates_passed: tuple
    reasons: tuple            # ((gate, text), ...)
    audit_head: str
    human_decision: object = None   # recorded human choice, if any

    @property
    def approval_granted(self):
        """The machine never approves: always False, and it can't be set."""
        return False


def close_loop(decision, steps, chain, human_decision=None):
    """decision: HUMAN_REVIEW or 144 HOLD from VERIFY / RECOVERY.
    steps: list of (gate, ok, reasons) in the order they ran."""
    passed, reasons = [], []
    for gate, ok, why in steps:
        if ok is True:
            passed.append(gate)
        else:
            reasons.extend(why or [(gate, "did not complete")])
    if not verify_chain(chain.entries):
        reasons.append(("999000 AUDIT", "audit chain broken"))
    balanced = not reasons and decision == HUMAN_REVIEW
    if decision != HUMAN_REVIEW and not reasons:
        reasons.append((GATE, "loop ended in 144 HOLD"))
    status = BALANCED if balanced else UNBALANCED
    outcome = HUMAN_REVIEW if balanced else HOLD
    chain.append(GATE, status, "; ".join("%s: %s" % r for r in reasons))
    return BalanceResult(outcome, status, tuple(passed), tuple(tuple(r) for r in reasons),
                         chain.head, human_decision)
