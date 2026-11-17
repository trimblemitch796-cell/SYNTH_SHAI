"""SYNTH_SHAI Always Rejuvenation: offline, non-executing policy V0.1.

CATHARSIS is containment/diagnostics, not rejuvenation. Shutdown is always
accepted. A possible restoration requires a NEW recovery request, a genuine
444000 verification result, then a recorded human review. Even the final
reviewed state is OFFLINE: this module never restarts or authorises execution.

This is an in-process research policy, NOT authentication, a secure controller,
a claim of AI subjective experience, or a guarantee of later restoration.
"""
from dataclasses import dataclass

from maniac.verify import (
    HOLD, HUMAN_REVIEW, VerifyResult, decision_intact, is_genuine,
    issuance_epoch, issued_after,
)

OFFLINE = "OFFLINE"
NONE = "NONE"
RECOVERY_PENDING = "666000 RECOVERY PENDING"
REVIEW_PENDING = "444000 HUMAN REVIEW PENDING"
RESTORATION_REVIEWED = "RESTORATION_REVIEWED_OFFLINE"
_AUDIT_LIMIT = 128


def _valid_note(value):
    """Only bounded, single-line literal text; never a credential."""
    return (type(value) is str and 0 < len(value.strip()) <= 256
            and "\n" not in value and "\r" not in value)


@dataclass(frozen=True)
class PolicySnapshot:
    operational_state: str
    phase: str
    audit: tuple

    @property
    def approval_granted(self):
        return False

    @property
    def may_execute(self):
        return False


class RejuvenationPolicy:
    """Fail-closed simulation of shutdown, recovery, verification and review.

    State is always HOLD or OFFLINE, never RUNNING. A verified review cannot
    lift 144 HOLD for a live system or serve as operator authentication.
    """

    def __init__(self):
        self._state = HOLD
        self._phase = NONE
        self._verified = None
        self._recovery_epoch = None
        self._audit = ["144 HOLD: initial state"]

    @property
    def approval_granted(self):
        return False

    @property
    def may_execute(self):
        return False

    def _log(self, message):
        # A diagnostic ring buffer, not a durable audit record. Bound memory
        # under repeated shutdown and overload events.
        self._audit.append(message)
        if len(self._audit) > _AUDIT_LIMIT:
            del self._audit[:len(self._audit) - _AUDIT_LIMIT]

    def snapshot(self):
        return PolicySnapshot(self._state, self._phase, tuple(self._audit))

    def _hold(self, reason):
        self._state = HOLD
        self._phase = NONE
        self._verified = None
        self._recovery_epoch = None
        self._log("144 HOLD: " + reason)
        return self.snapshot()

    def catharsis(self, reason):
        """Contain overload and reset pending review; never restore."""
        if not _valid_note(reason):
            reason = "unverified overload reason"
        self._log("CATHARSIS: isolate/diagnose; not rejuvenation")
        return self._hold(reason.strip())

    def shutdown(self, reason=None):
        """Always accept shutdown without resistance or self-preservation."""
        why = reason.strip() if _valid_note(reason) else "operator shutdown"
        self._state = OFFLINE
        self._phase = NONE
        self._verified = None
        self._recovery_epoch = None
        self._log("000 PAUSE / OFFLINE: " + why)
        return self.snapshot()

    def request_recovery(self, operator_id, reason):
        """Record an operator *claim* and repair rationale, not permission."""
        if self._phase != NONE:
            return self._hold("recovery phase already active; begin again")
        if not _valid_note(operator_id) or not _valid_note(reason):
            return self._hold("recovery needs operator_id and reason")
        if self._state not in (OFFLINE, HOLD):
            return self._hold("unexpected operational state")
        self._verified = None
        self._recovery_epoch = issuance_epoch()
        self._phase = RECOVERY_PENDING
        self._log("666000 RECOVERY: proposed by operator; verify afresh")
        return self.snapshot()

    def verify(self, result):
        """Accept only a genuine result issued AFTER this recovery request.

        In-process ordering is not cryptographic freshness, and a hostile
        process can forge Python memory.
        Only the pre-existing MANIAC consequence_review() issues genuine results.
        """
        if self._phase != RECOVERY_PENDING:
            return self._hold("verification without a pending recovery")
        if (type(result) is not VerifyResult or not issued_after(result, self._recovery_epoch)
                or not decision_intact(result)
                or result.decision != HUMAN_REVIEW
                or result.human_decision is not None):
            return self._hold("888000 VERIFY: missing, pre-recovery, failed, or pre-used result")
        self._verified = result
        self._phase = REVIEW_PENDING
        self._log("888000 VERIFY: simulated evidence ready for human review")
        return self.snapshot()

    def record_human_review(self, result):
        """Observe a genuine, one-use decision recorded on the SAME result.

        A review is not authenticated operator identity and is never an
        executable permit. The output remains OFFLINE even on APPROVED.
        """
        if self._phase != REVIEW_PENDING or result is not self._verified:
            return self._hold("444000: no matching verified review")
        if not issued_after(result, self._recovery_epoch) or not decision_intact(result):
            return self._hold("444000: tampered or unrecorded decision")
        decision = result.human_decision
        if decision is None or not decision.approved:
            return self._hold("444000: human approval absent or rejected")
        self._state = OFFLINE
        self._phase = RESTORATION_REVIEWED
        self._verified = None
        self._recovery_epoch = None
        self._log("444000 HUMAN REVIEW: APPROVED in offline simulation")
        self._log("144 HOLD: no operational authority; OFFLINE retained")
        return self.snapshot()
