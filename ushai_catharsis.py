"""USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1).

USHAI Catharsis gate written by Mitch Trimble. Offline only; it never
grants operational authority. Small safety fixes are marked "FIX n".
"""
from dataclasses import dataclass, fields
from enum import Enum


class State(str, Enum):
    # MONITOR and SAFE_LOCK are reserved for MONITOR SYSTEM integration.
    MONITOR = "MONITOR"
    HOLD = "144 HOLD"
    REVIEW = "REVIEW_REQUIRED"
    SAFE_LOCK = "SAFE_LOCK"


@dataclass(frozen=True)
class EthicalEvidence:
    intent_defined: bool
    consent_verified: bool
    evidence_verified: bool
    contradiction_found: bool
    harmful_consequence_found: bool
    uncertainty_resolved: bool


class USHAICatharsis:
    """Offline ethical decision gate. Never grants operational authority."""

    approval_granted = False  # FIX 5: this gate can never approve anything

    def __init__(self):
        self.state = State.HOLD
        self.audit = []
        self.reason = ""

    def assess(self, evidence):
        # FIX 2: fresh audit and state for every call, so an old REVIEW can't leak in.
        self.state = State.HOLD
        self.audit = []
        try:
            return self._assess(evidence)
        except Exception as exc:  # FIX 1: any crash fails closed
            return self.hold("Internal error: %s" % type(exc).__name__)

    def _assess(self, evidence):
        self.audit.append("000 PAUSE / ASSESS")
        # FIX 1: only a real EthicalEvidence with real bools is accepted.
        # A string like "False" is truthy and used to pass every check.
        if not isinstance(evidence, EthicalEvidence):
            return self.hold("Evidence is not EthicalEvidence")
        for f in fields(evidence):
            if type(getattr(evidence, f.name)) is not bool:
                return self.hold("Field %s is not a real True/False" % f.name)

        # FIX 3: each gate is logged as "checked" next to the test it runs.
        self.audit.append("111 IDENTIFY INTENT: checked")
        if not evidence.intent_defined:
            return self.hold("Undefined intent")
        self.audit.append("222 OBSERVE RAW / 333 DEFINE PROBLEM / 333000 RECORD: consent checked")
        if not evidence.consent_verified:
            return self.hold("Consent unverified")
        self.audit.append("777000 RECEIVE EVIDENCE: checked")
        if not evidence.evidence_verified:
            return self.hold("Evidence unverified")
        self.audit.append("555000 TRIANGULATE: checked")
        if evidence.contradiction_found:
            return self.hold("Contradiction detected")
        self.audit.append("888000 CHECK LOOP / CONSEQUENCE REVIEW: checked")
        if evidence.harmful_consequence_found:
            return self.hold("Potential harmful consequence")
        if not evidence.uncertainty_resolved:
            return self.hold("Unresolved uncertainty")

        self.state = State.REVIEW
        self.reason = "Evidence sufficient; a human must decide"
        self.audit.append("444000 VERIFY")
        self.audit.append("HUMAN REVIEW")
        self._close_audit()
        return self.state.value

    def hold(self, reason):
        self.state = State.HOLD
        self.reason = reason
        self.audit.append(f"144 HOLD: {reason}")
        self._close_audit()
        return self.state.value

    def _close_audit(self):
        # FIX 3: Mitch's flow - both branches end the same way.
        self.audit += ["222000 RE-OBSERVE", "111000 COMPARE / LEARN",
                       "999000 AUDIT", "Δ BALANCE"]

    def propose_recovery(self):
        # FIX 4: only from HOLD, stays HOLD; caller must assess() NEW evidence.
        if self.state is not State.HOLD:
            return self.state.value
        self.audit += ["1301133 REPAIR / REFRAME", "666000 RECOVERY"]
        self.state = State.HOLD
        return "REVERIFY_REQUIRED"
