"""The MANIAC chain in one call (offline simulation only - no hardware):
MONITOR SYSTEM -> CHECK EVIDENCE -> 555000 TRIANGULATE -> 444000 VERIFY.
"""
from maniac.evidence import check_evidence, no_trusted_replay_store
from maniac.triangulate import triangulate, readings_from_bundle
from maniac.verify import VerifyResult, HOLD


def run_chain(supervisor, request, monitor, bundle, clock):
    """Returns a VerifyResult: 144 HOLD or HUMAN_REVIEW (never approval)."""
    try:
        snap = monitor.snapshot()
        if snap["state"] == "SAFE_LOCK":
            return VerifyResult(HOLD, [("MONITOR SYSTEM", snap["reason"])],
                                ["monitor human_reset() first"])
        checker = getattr(supervisor, "provenance_checker", no_trusted_replay_store)
        evidence = check_evidence(bundle, clock, provenance_checker=checker)
        tri = triangulate(readings_from_bundle(bundle))
        return supervisor.review(request, snap, evidence, tri)
    except Exception as exc:  # fail closed
        return VerifyResult(HOLD, [("CHAIN", "internal error: %s" % type(exc).__name__)])
