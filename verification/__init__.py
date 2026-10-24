"""SYNTH_SHAI verification and safety checks package."""

"""SYNTH_SHAI evidence-presence gate (not an approval mechanism)."""
from collections.abc import Mapping

HOLD = "144 HOLD"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
REQUIRED_FIELDS = ("test_report", "source_revision", "verification_evidence")


def verify_result(result):
    """Require nonempty evidence fields before escalating to human review.

    This checks presence only, not authenticity or correctness of evidence.
    It never authorizes deployment, physical actuation, or bypass of HOLD.
    """
    if not isinstance(result, Mapping):
        return HOLD
    if not all(result.get(field) for field in REQUIRED_FIELDS):
        return HOLD
    return REVIEW_REQUIRED
