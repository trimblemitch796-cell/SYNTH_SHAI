"""555000 TRIANGULATE (offline simulation only - controls no hardware).

Needs at least two INDEPENDENT sources that agree.
"Independent" here means every reading has its own source_id AND its own
source_type (channel). Two cameras are the same type, so they are not
independent of each other - a camera plus a lidar is.

Result: "PASS" with an agreed value and a confidence, or "144 HOLD".
PASS is not approval. Anything odd fails closed to 144 HOLD.
"""
from dataclasses import dataclass, field

from maniac.evidence import TOLERANCE, is_real_number, relative_spread

HOLD = "144 HOLD"
PASS = "PASS"
GATE = "555000 TRIANGULATE"
MIN_SOURCES = 2


@dataclass(frozen=True)   # frozen: fields can't be changed after creation
class TriangulationResult:
    outcome: str
    value: object = None          # agreed value (median), None on HOLD
    confidence: float = 0.0       # 1.0 = perfect agreement, 0.0 = at the tolerance edge
    reasons: list = field(default_factory=list)   # [(gate, text), ...]
    sources: list = field(default_factory=list)


def triangulate(readings, tolerance=TOLERANCE, min_sources=MIN_SOURCES):
    """readings: list of {"source_id": str, "source_type": str, "value": number}."""
    reasons = []

    def hold(text):
        reasons.append((GATE, text))

    try:
        if not isinstance(readings, list):
            hold("readings must be a list")
            return TriangulationResult(HOLD, reasons=reasons)
        ids, types, values = [], [], []
        for r in readings:
            if not isinstance(r, dict) or set(r) != {"source_id", "source_type", "value"}:
                hold("malformed reading %r" % (r,))
                continue
            sid, stype, value = r["source_id"], r["source_type"], r["value"]
            if not (isinstance(sid, str) and sid.strip() and isinstance(stype, str) and stype.strip()):
                hold("source_id and source_type must be non-empty text")
                continue
            if not is_real_number(value):
                hold("source %r: value is not a real number" % sid)
                continue
            ids.append(sid); types.append(stype); values.append(value)

        # Independence: no repeated id, no repeated type
        if len(set(ids)) != len(ids):
            hold("the same source_id appears twice")
        if len(set(types)) != len(types):
            hold("sources share a type, so they are not independent")
        if len(values) < min_sources:
            hold("fewer than %d independent sources" % min_sources)
        if reasons:
            return TriangulationResult(HOLD, reasons=reasons, sources=ids)

        spread = relative_spread(values)
        if spread > tolerance:
            hold("sources disagree by %.1f%% (limit %.1f%%)" % (spread * 100, tolerance * 100))
            return TriangulationResult(HOLD, reasons=reasons, sources=ids)

        ordered = sorted(values)
        mid = len(ordered) // 2
        median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
        confidence = round(1.0 - spread / tolerance, 3) if tolerance > 0 else 0.0
        return TriangulationResult(PASS, median, confidence, [], ids)
    except Exception as exc:  # fail closed
        hold("internal error: %s" % type(exc).__name__)
        return TriangulationResult(HOLD, reasons=reasons)


def readings_from_bundle(bundle, quantity="distance"):
    """Turn CHECK EVIDENCE sensor readings into TRIANGULATE readings.
    A sensor's type comes from its "type" field (falls back to its source name)."""
    out = []
    for s in bundle.get("sensors", []) if isinstance(bundle, dict) else []:
        if isinstance(s, dict) and s.get("quantity") == quantity:
            out.append({"source_id": s.get("source"),
                        "source_type": s.get("type", s.get("source")),
                        "value": s.get("value")})
    return out
