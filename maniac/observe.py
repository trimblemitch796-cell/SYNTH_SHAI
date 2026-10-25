"""222000 RE-OBSERVE (offline simulation only - controls no hardware).

After a decision (human decision or recovery), take a FRESH observation
and check the world matches what was expected. Any mismatch -> 144 HOLD.
"""
from maniac.evidence import TOLERANCE, is_real_number, relative_spread
from maniac.triangulate import triangulate, PASS

GATE = "222000 RE-OBSERVE"


def reobserve(expected_value, readings, tolerance=TOLERANCE):
    """Returns (ok, reasons). readings use the TRIANGULATE format."""
    try:
        if not is_real_number(expected_value):
            return False, [(GATE, "no expected value to compare with")]
        tri = triangulate(readings, tolerance=tolerance)
        if tri.outcome != PASS:
            return False, [(GATE, text) for _, text in tri.reasons]
        if relative_spread([expected_value, tri.value]) > tolerance:
            return False, [(GATE, "world does not match: expected %s, observed %s"
                            % (expected_value, tri.value))]
        return True, []
    except Exception as exc:  # fail closed
        return False, [(GATE, "internal error: %s" % type(exc).__name__)]
