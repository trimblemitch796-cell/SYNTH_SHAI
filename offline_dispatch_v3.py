"""SHAI Security V3: enforced gate on a fixed, simulation-only dispatcher.

No user-supplied handler, arbitrary callback, command execution, network
client, disk write, or real-world effects. This is NOT an OS isolation boundary.
"""
from dataclasses import dataclass
from offline_approval_v1 import HOLD
from offline_preflight_v3 import REVIEW, evaluate_preflight

SIMULATED = "SIMULATED_REVIEW_ONLY"
_ALLOWED_SIMULATIONS = frozenset(("synthetic_review",))


@dataclass(frozen=True)
class DispatchResult:
    decision: str
    simulated_effect: str | None = None


def dispatch_simulation(request, approval, *, policy, trusted_operator_keys,
                        trusted_database_path, now):
    """Enforce signed approval at the only entry to fixed synthetic operations.

    An allowlist in the policy cannot expand the hard-coded simulator. Denied
    requests cannot reach the simulated effect. A successful signature is
    consumed at this boundary, so replay cannot repeat the simulated effect.
    """
    try:
        if type(request) is not dict or request.get("action") not in _ALLOWED_SIMULATIONS:
            return DispatchResult(HOLD)
        result = evaluate_preflight(
            request, approval,
            policy=policy, trusted_operator_keys=trusted_operator_keys,
            trusted_database_path=trusted_database_path, now=now)
        if result != REVIEW:
            return DispatchResult(HOLD)
        # Fixed transformation ONLY. No dynamic call, eval, import or IO.
        return DispatchResult(SIMULATED, "synthetic_review_recorded")
    except (TypeError, ValueError, KeyError, AttributeError):
        return DispatchResult(HOLD)
