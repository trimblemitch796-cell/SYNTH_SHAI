"""Pure, read-only SHAI evidence *triage* for the ChatGPT MCP prototype.

This is not an approval mechanism, security sandbox or independent validator.
No filesystem writes, network access, subprocesses or external accounts.
"""
from __future__ import annotations

from hashlib import sha256
import re

MAIN_SNAPSHOT = "13987e18d172f334a202c54f38e28782a4e45fcc"
_RUN_URL = re.compile(
    r"https://github\.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/[1-9][0-9]{0,19}\Z"
)
_SHA = re.compile(r"[0-9a-fA-F]{40}\Z")


def shai_status_snapshot() -> dict:
    """A fixed, dated snapshot, not live GitHub access or independent verification."""
    return {
        "project": "SYNTH_SHAI",
        "snapshot_date": "2026-11-06",
        "source_revision": MAIN_SNAPSHOT,
        "source_url": "https://github.com/trimblemitch796-cell/SYNTH_SHAI/commit/" + MAIN_SNAPSHOT,
        "capability": "Offline research and human-supervised review only",
        "authorization": "144 HOLD",
        "project_maintained_ci": {
            "result": "success on the indicated snapshot; scope is project-authored tests",
            "url": "https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/41740315033",
        },
        "known_limitations": [
            "No independently validated operational safety",
            "No deployed Android-to-model connection in this MCP prototype",
            "No full OS filesystem, network, descendant or IPC isolation",
            "No verified autonomous execution or financial, medical or robotics authority",
            "This tool cannot query current GitHub status; snapshot can become stale",
        ],
        "tool_policy": {
            "read_only": True,
            "external_calls": False,
            "approval_granted": False,
            "consequential_action_state": "144 HOLD",
        },
    }


def shai_triage_evidence(claim: str, source_revision: str = "", evidence_url: str = "") -> dict:
    """Check input presence/shape ONLY. It never verifies the evidence or grants authority.

    Claim contents are not returned; only a SHA-256 fingerprint to avoid
    passing model instructions embedded in a claim back as tool output.
    """
    base = {
        "approval_granted": False,
        "consequential_action_state": "144 HOLD",
        "external_verification_performed": False,
        "evidence_authenticated": False,
        "meaning": "Syntactic intake only, NOT fact-checking or approval",
    }
    if not isinstance(claim, str) or not claim.strip() or len(claim) > 1000:
        return {**base, "decision": "144 HOLD", "reason": "invalid_or_missing_claim"}
    digest = sha256(claim.strip().encode("utf-8")).hexdigest()
    if not isinstance(source_revision, str) or not _SHA.fullmatch(source_revision):
        return {**base, "decision": "144 HOLD", "reason": "missing_or_invalid_commit_sha", "claim_sha256": digest}
    if not isinstance(evidence_url, str) or not _RUN_URL.fullmatch(evidence_url):
        return {**base, "decision": "144 HOLD", "reason": "missing_or_invalid_project_run_url", "claim_sha256": digest}
    return {
        **base,
        "decision": "REVIEW_REQUIRED",
        "reason": "source_reference_format_present_but_unverified",
        "claim_sha256": digest,
        "candidate_revision": source_revision.lower(),
        "next_step": "Human checks exact revision, CI job logs and independent evidence; no action authorized",
    }
