"""444000 VERIFY / HUMAN APPROVAL - the CONSEQUENCE REVIEW split.

(offline simulation only - controls no hardware)

Combines every layer and collects ALL their reasons (not just the first):
  USHAI ETHICAL CONSCIENCE, MONITOR SYSTEM, CHECK EVIDENCE,
  555000 TRIANGULATE, and (optionally) the supervisor's own result.

  RISK / ERROR FOUND  -> 144 HOLD, next: 1301133 REPAIR -> 666000 RECOVERY
  EVIDENCE SUFFICIENT -> HUMAN_REVIEW (never approval)

Only record_human_decision() - an explicit human choice - can approve.
"""
from dataclasses import dataclass, field

from maniac.evidence import EvidenceResult, PASS as EVIDENCE_PASS
from maniac.triangulate import TriangulationResult, PASS as TRI_PASS
from ushai_catharsis import USHAICatharsis, State

HOLD = "144 HOLD"
HUMAN_REVIEW = "HUMAN_REVIEW"
HOLD_NEXT_STEPS = ["1301133 BUILD / REPAIR / REFRAME", "666000 RECOVERY"]
REVIEW_NEXT_STEPS = ["HUMAN REVIEW"]
# Follow-up gates on BOTH branches - built in step 6, pending for now.
PENDING_GATES = ["222000 RE-OBSERVE", "111000 COMPARE / LEARN", "999000 AUDIT", "Δ BALANCE"]
HUMAN_CHOICES = ("APPROVED", "REJECTED")


@dataclass(frozen=True)
class HumanDecision:
    operator_id: str
    decision: str          # "APPROVED" or "REJECTED"
    reason: str

    @property
    def approved(self):
        return self.decision == "APPROVED"


@dataclass
class VerifyResult:
    decision: str
    reasons: list = field(default_factory=list)     # [(layer, text), ...] from EVERY layer
    next_steps: list = field(default_factory=list)
    pending_gates: list = field(default_factory=lambda: list(PENDING_GATES))
    approval_granted: bool = False                  # the machine never approves
    human_decision: object = None

    def __post_init__(self):
        self.approval_granted = False

    def record_human_decision(self, operator_id, decision, reason):
        """The ONLY way something can be approved: an explicit human choice.
        Raises ValueError for anything that isn't clearly valid."""
        if self.decision != HUMAN_REVIEW:
            raise ValueError("a 144 HOLD cannot be approved; repair and re-verify first")
        if self.human_decision is not None:
            raise ValueError("a human decision was already recorded")
        for name, value in (("operator_id", operator_id), ("reason", reason)):
            # type(...) is str rejects True/1/None; strip() rejects "   "
            if type(value) is not str or not value.strip():
                raise ValueError("%s must be non-empty text" % name)
        # Exact words only: "yes", "true", "approved", True are all refused
        if type(decision) is not str or decision not in HUMAN_CHOICES:
            raise ValueError("decision must be exactly 'APPROVED' or 'REJECTED'")
        self.human_decision = HumanDecision(operator_id.strip(), decision, reason.strip())
        return self.human_decision


def consequence_review(ushai, monitor_snapshot, evidence_result, triangulation,
                       supervisor_result=None):
    """Check every layer and gather all reasons. Any reason = 144 HOLD."""
    reasons = []
    try:
        # USHAI ETHICAL CONSCIENCE: must be a gate that said REVIEW_REQUIRED
        if not isinstance(ushai, USHAICatharsis) or ushai.state is not State.REVIEW:
            why = getattr(ushai, "reason", "") or "not assessed"
            reasons.append(("USHAI ETHICAL CONSCIENCE", why))

        # MONITOR SYSTEM
        if not isinstance(monitor_snapshot, dict) or monitor_snapshot.get("state") != "MONITOR":
            why = monitor_snapshot.get("reason") if isinstance(monitor_snapshot, dict) else "no snapshot"
            reasons.append(("MONITOR SYSTEM", why))

        # CHECK EVIDENCE - copy every one of its reasons
        if not isinstance(evidence_result, EvidenceResult) or evidence_result.overall != EVIDENCE_PASS:
            for gate, text in getattr(evidence_result, "reasons", None) or [("", "no evidence result")]:
                reasons.append(("CHECK EVIDENCE " + gate, text))

        # 555000 TRIANGULATE
        if not isinstance(triangulation, TriangulationResult) or triangulation.outcome != TRI_PASS:
            for gate, text in getattr(triangulation, "reasons", None) or [("", "no triangulation")]:
                reasons.append((gate or "555000 TRIANGULATE", text))

        # Supervisor (optional)
        if supervisor_result is not None and getattr(supervisor_result, "decision", None) != HUMAN_REVIEW:
            reasons.append(("SUPERVISOR", getattr(supervisor_result, "reason", "bad result")))
    except Exception as exc:  # fail closed
        reasons.append(("444000 VERIFY", "internal error: %s" % type(exc).__name__))

    if reasons:
        return VerifyResult(HOLD, reasons, list(HOLD_NEXT_STEPS))
    return VerifyResult(HUMAN_REVIEW, [], list(REVIEW_NEXT_STEPS))
