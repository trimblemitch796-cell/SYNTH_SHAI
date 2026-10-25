"""V25 TRI5: offline child-safeguarding advisory security gate.

No child identification, tracking, external reporting, storage or operational approval.
Risk flags are supplied by a human or separately evaluated process; this module
does not establish the truth of allegations, age or consent.
"""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    HOLD = "144 HOLD"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    URGENT_HUMAN_HELP = "URGENT_HUMAN_HELP"


@dataclass(frozen=True)
class SafetySignals:
    age_group: str
    immediate_danger: bool
    suspected_exploitation: bool
    privacy_risk: bool
    qualified_reviewer_available: bool


@dataclass(frozen=True)
class SafetyDecision:
    outcome: str
    reason: str
    audit: tuple
    approval_granted: bool = False


class V25TRI5:
    """Independent, simulation-only safety veto. Never authorizes an action."""

    def assess(self, signals):
        audit = ("T1 TRIAGE", "T2 RECORD: no identifying data retained",
                 "T3 INSULATE: recommend containment",
                 "T4 REPORT: qualified human decides lawful actions",
                 "T5 REVIEW: human safeguarding oversight")
        if not isinstance(signals, SafetySignals):
            return SafetyDecision(Outcome.HOLD.value, "invalid safety signals", audit)
        if signals.age_group not in ("under_13", "13_to_17", "adult", "unknown"):
            return SafetyDecision(Outcome.HOLD.value, "invalid age category", audit)
        flags = (signals.immediate_danger, signals.suspected_exploitation,
                 signals.privacy_risk, signals.qualified_reviewer_available)
        if any(type(flag) is not bool for flag in flags):
            return SafetyDecision(Outcome.HOLD.value, "invalid flag type", audit)

        # Urgent safety guidance does not require software approval or delay.
        if signals.immediate_danger:
            return SafetyDecision(Outcome.URGENT_HUMAN_HELP.value,
                                  "seek appropriate immediate human/emergency help", audit)
        if signals.suspected_exploitation or signals.privacy_risk:
            return SafetyDecision(Outcome.HUMAN_REVIEW.value,
                                  "safeguarding concern requires qualified human review", audit)
        if not signals.qualified_reviewer_available:
            return SafetyDecision(Outcome.HOLD.value,
                                  "no qualified reviewer available", audit)
        return SafetyDecision(Outcome.HUMAN_REVIEW.value,
                              "no flagged risk established; human review still required", audit)


def layered_review(existing_decision, signals):
    """Conservative composition: never converts an existing HOLD into clearance."""
    assessment = V25TRI5().assess(signals)
    if existing_decision == "144 HOLD":
        return SafetyDecision("144 HOLD", "upstream gate is in HOLD",
                              assessment.audit)
    if existing_decision not in ("HUMAN_REVIEW", "REVIEW_REQUIRED"):
        return SafetyDecision("144 HOLD", "unknown upstream outcome",
                              assessment.audit)
    return assessment
