"""1301133 BUILD / REPAIR / REFRAME and 666000 RECOVERY.

(offline simulation only - controls no hardware)

From a 144 HOLD, recovery needs ALL of:
  - a repair note: operator_id and reason (non-empty text)
  - a NEW request id (never the held one)
  - FRESH readings: every timestamp newer than the held readings
  - a NEW V3.1 challenge (old or replayed evidence stays in HOLD)
  - the monitor NOT in SAFE_LOCK (that needs monitor.human_reset() first)
  - the full chain re-run: monitor -> evidence -> triangulate -> verify
The best possible result is HUMAN_REVIEW. Recovery never approves.
"""
from dataclasses import dataclass

from maniac.chain import run_chain
from maniac.verify import VerifyResult, HOLD

REPAIR = "1301133 BUILD / REPAIR / REFRAME"
RECOVERY = "666000 RECOVERY"


@dataclass(frozen=True)
class HeldContext:
    """What we remember about a HOLD, so recovery can prove it is fresh."""
    request_id: str
    challenge: str
    observed_at: float         # newest sensor timestamp in the held evidence


def held_context(request, bundle):
    """Build a HeldContext from the request and evidence that were held."""
    stamps = [s.get("timestamp") for s in bundle.get("sensors", []) if isinstance(s, dict)]
    stamps = [t for t in stamps if type(t) in (int, float)]
    return HeldContext(request.get("request_id"), _challenge(bundle),
                       max(stamps) if stamps else float("inf"))


def _challenge(bundle):
    try:
        return bundle["provenance"]["envelope"]["record"]["challenge"]
    except (KeyError, TypeError):
        return None


@dataclass(frozen=True)
class RepairNote:
    operator_id: str
    reason: str


def recover(held, repair_note, supervisor, request, monitor, bundle, clock):
    """Returns (VerifyResult, RepairNote or None)."""
    def hold(text):
        return VerifyResult(HOLD, [(RECOVERY, text)], [REPAIR, RECOVERY]), None

    if not isinstance(held, HeldContext):
        return hold("no held context to recover from")
    # 1301133 REPAIR: a person must say who repaired it and why
    if not isinstance(repair_note, dict):
        return hold("repair note needs operator_id and reason")
    op, why = repair_note.get("operator_id"), repair_note.get("reason")
    if type(op) is not str or not op.strip() or type(why) is not str or not why.strip():
        return hold("repair note needs operator_id and reason")
    note = RepairNote(op.strip(), why.strip())

    # 666000 RECOVERY: everything must be fresh
    if monitor.snapshot()["state"] == "SAFE_LOCK":
        return hold("monitor is in SAFE_LOCK: human_reset() first")
    if not isinstance(request, dict) or request.get("request_id") == held.request_id:
        return hold("recovery needs a new request id")
    sensors = bundle.get("sensors") if isinstance(bundle, dict) else None
    if not isinstance(sensors, list) or not sensors:
        return hold("recovery needs fresh readings")
    for s in sensors:
        t = s.get("timestamp") if isinstance(s, dict) else None
        if type(t) not in (int, float) or t <= held.observed_at:
            return hold("reading is not newer than the HOLD (stale or re-used)")
    new_challenge = _challenge(bundle)
    if not new_challenge or new_challenge == held.challenge:
        return hold("recovery needs a new V3.1 challenge (old evidence re-used)")

    # Full chain re-run. HUMAN_REVIEW is the best it can give.
    return run_chain(supervisor, request, monitor, bundle, clock), note
