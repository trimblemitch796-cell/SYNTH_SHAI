"""SHAI read-only research -> fixed synthetic action review, offline only.

NOT an authorization service, ChatGPT tool, public API, GitHub writer, or
trusted execution boundary. Evidence intake validates FORMAT ONLY.
The synthetic action is gated by the existing one-use Ed25519 reviewer path.
"""
from dataclasses import dataclass

from plugins.shai_mcp_v01.core import shai_triage_evidence
from offline_approval_v1 import HOLD
from offline_dispatch_v3 import dispatch_simulation


@dataclass(frozen=True)
class StagedResult:
    evidence_decision: str
    action_decision: str
    simulated_effect: str | None = None
    external_action_performed: bool = False
    consequential_action_state: str = HOLD


def research_then_synthetic_review(
    claim, source_revision, evidence_url, request, approval, *,
    policy, trusted_operator_keys, trusted_database_path, now
):
    """Return a bounded local result. Never invoke real external capabilities.

    Syntactically valid evidence does not authenticate provenance or grant
    permission. Only an existing signed, one-use approval can reach the
    fixed synthetic_review effect, and that effect has no external side effect.
    The caller must never interpret SIMULATED as a production release permit.
    """
    try:
        triage = shai_triage_evidence(claim, source_revision, evidence_url)
        evidence_decision = triage["decision"]
        if evidence_decision != "REVIEW_REQUIRED":
            return StagedResult(evidence_decision, HOLD)
        simulation = dispatch_simulation(
            request, approval, policy=policy,
            trusted_operator_keys=trusted_operator_keys,
            trusted_database_path=trusted_database_path, now=now,
        )
        return StagedResult(
            evidence_decision, simulation.decision, simulation.simulated_effect
        )
    except (TypeError, ValueError, KeyError, AttributeError):
        return StagedResult(HOLD, HOLD)
