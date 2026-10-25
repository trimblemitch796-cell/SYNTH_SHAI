"""SYNTH_SHAI Super Tool V1 — offline ASK/CHECK/BUILD prototype.

Deterministic document helper; NOT an AI model, web service, safety certification,
or autonomous executor. Never runs generated code or takes external actions.
"""
from dataclasses import dataclass
from enum import Enum
import re


class Mode(str, Enum):
    ASK = "ASK"
    CHECK = "CHECK"
    BUILD = "BUILD"


@dataclass(frozen=True)
class ToolResult:
    mode: str
    status: str
    output: str
    evidence_needed: tuple
    human_review_required: bool = True
    approval_granted: bool = False


MAX_CHARS = 4000
_BLOCKED_ACTIONS = (
    "execute", "deploy", "send email", "transfer money",
    "control robot", "enable actuator", "track child",
)


def run(mode, request, *, evidence=(), child_safety_concern=False):
    """Process short offline text; never grant operational permission."""
    if not isinstance(mode, str) or mode not in Mode._value2member_map_:
        return _hold("Unknown mode")
    if not isinstance(request, str) or not request.strip() or len(request) > MAX_CHARS:
        return _hold("Missing or oversized request", mode)
    if not isinstance(evidence, (tuple, list)) or any(
        not isinstance(item, str) or len(item) > MAX_CHARS for item in evidence
    ):
        return _hold("Invalid evidence format", mode)
    if type(child_safety_concern) is not bool:
        return _hold("Invalid safeguarding flag", mode)
    if child_safety_concern:
        return _hold("Safeguarding concern: qualified human review required", mode)
    lowered = request.casefold()
    if any(re.search(r"\b" + re.escape(term) + r"\b", lowered) for term in _BLOCKED_ACTIONS):
        return _hold("Operational action outside offline prototype scope", mode)

    summary = " ".join(request.strip().split())
    if mode == Mode.ASK:
        output = "Question to investigate: " + summary + "\nNo model inference or external research has been performed."
        needs = ("Authoritative references", "Assumptions and context")
    elif mode == Mode.CHECK:
        output = ("Claim to verify: " + summary + "\nProvided evidence items: " +
                  str(len(evidence)) + "\nUnverified pending human source review.")
        needs = ("Independent corroboration", "Source provenance", "Contradictory evidence")
    else:
        output = ("DRAFT FOR HUMAN REVIEW\nObjective: " + summary +
                  "\n1. Define success criteria\n2. Gather evidence\n"
                  "3. Draft solution\n4. Test offline\n5. Request human review")
        needs = ("Acceptance criteria", "Risk assessment", "Test evidence")
    return ToolResult(mode, "HUMAN_REVIEW", output, needs)


def _hold(reason, mode="UNKNOWN"):
    return ToolResult(mode, "144 HOLD", reason, ("Clarify request and permissions",))
