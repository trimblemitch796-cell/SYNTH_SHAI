"""SYNTH_SHAI V3 research: default-deny, NON-EXECUTING authorization preflight.

No callback, actuator, network, file-write action, or dispatch interface exists.
Trusted policy and Ed25519 keys must be supplied by a separate trusted host.
A passing result is a human-review recommendation, never an execution permit.
"""
from dataclasses import dataclass
from offline_approval_v1 import HOLD, VALIDATED, _valid_request, validate_once

REVIEW = "REVIEW_REQUIRED_NO_EXECUTION"
PROHIBITED = frozenset((
    "send_message", "transfer_funds", "move_robot", "deploy_code",
    "delete_data", "run_command", "access_camera", "access_microphone",
))


@dataclass(frozen=True)
class PreflightPolicy:
    allowed_actions: frozenset
    prohibited_actions: frozenset = PROHIBITED


def evaluate_preflight(request, approval, *, policy, trusted_operator_keys,
                       trusted_database_path, now):
    """Check policy BEFORE consuming a signed approval.

    Only a strict allowlist action is considered, and no real operation is
    ever performed. All unexpected configurations and inputs result in HOLD.
    """
    try:
        if type(policy) is not PreflightPolicy or not _valid_request(request):
            return HOLD
        allowed = policy.allowed_actions
        prohibited = policy.prohibited_actions
        if type(allowed) is not frozenset or type(prohibited) is not frozenset:
            return HOLD
        if not allowed or any(type(x) is not str or not x for x in allowed | prohibited):
            return HOLD
        if not PROHIBITED.issubset(prohibited):
            return HOLD
        if allowed & prohibited:
            return HOLD
        action = request["action"]
        if action not in allowed or action in prohibited:
            return HOLD
        # This module cannot execute an action: validate_once only consumes a
        # one-use signed approval and returns VALIDATED_NO_EXECUTION.
        decision = validate_once(
            request, approval, trusted_operator_keys=trusted_operator_keys,
            trusted_database_path=trusted_database_path, now=now)
        return REVIEW if decision == VALIDATED else HOLD
    except (TypeError, ValueError, KeyError, AttributeError):
        return HOLD
