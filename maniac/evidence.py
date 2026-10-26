"""MANIAC CHECK EVIDENCE (offline simulation only - controls no hardware).

Four checks, all fail closed:
  1. Sensor validity  - numeric, finite, inside its valid range, not stale
  2. Contradictions   - same quantity from different sources must agree
  3. Permissions      - action must be explicitly inside unexpired human consent
  4. Provenance       - V3.1 bridge (shai_v31_bridge.py) must say exactly
                        REVIEW_REQUIRED

The result is only "144 HOLD" or "PASS". PASS is NOT approval - it only
means the evidence may go on to 444000 VERIFY / HUMAN APPROVAL.
approval_granted is always False.
"""
from dataclasses import dataclass, field
import math

HOLD = "144 HOLD"
PASS = "PASS"

# Mitch's official gate names used in reasons / audit
G_OBSERVE_RAW = "222 OBSERVE RAW"
G_RECEIVE = "777000 RECEIVE EVIDENCE"
G_TRIANGULATE = "555000 TRIANGULATE"
G_VERIFY = "444000 VERIFY / HUMAN APPROVAL"

MAX_AGE = 2.0       # seconds before a sensor reading is stale
TOLERANCE = 0.05    # 5 % relative disagreement allowed (same as supervisor)
STUCK_COUNT = 5     # same value this many times in a row = stuck sensor

ALLOWED_FIELDS = {"sensors", "action", "consent", "provenance"}


def is_real_number(x):
    """True only for a finite int/float. bool is rejected (Python treats True as 1)."""
    try:
        return type(x) in (int, float) and math.isfinite(x)
    except OverflowError:
        return False


def relative_spread(values):
    """How far apart the values are, as a fraction of the biggest one.
    Shared by CHECK EVIDENCE and 555000 TRIANGULATE."""
    scale = max(abs(v) for v in values) or 1.0
    return (max(values) - min(values)) / scale


@dataclass(frozen=True)   # frozen: fields can't be changed after creation
class EvidenceResult:
    overall: str
    reasons: list = field(default_factory=list)   # [(gate, text), ...]
    audit: list = field(default_factory=list)

    @property
    def approval_granted(self):
        """Always False. A read-only property, so it can never be set to True."""
        return False


PROVENANCE_FIELDS = {"envelope"}   # the replay store is NEVER chosen by the request


class BridgeChecker:
    """Provenance checker bound to trusted configuration.

    replay_db: the ONE replay database (never chosen by the request).
    trust:     shai_v31_bridge.TrustConfig of pinned signing keys (never taken
               from the envelope). None -> every provenance check HOLDs.
    Challenges are ISSUED by this verifier (issue_challenge) and each one is
    single-use: an envelope whose record challenge was not issued here, or was
    already presented, fails closed to 144 HOLD.
    """

    def __init__(self, replay_db, trust=None):
        import os
        if not isinstance(replay_db, (str, os.PathLike)) or not os.fspath(replay_db):
            raise ValueError("replay_db must be a non-empty path from trusted configuration")
        self.replay_db = os.fspath(replay_db)
        self._trust = trust
        self._issued = {}          # challenge -> expected report sha256

    def issue_challenge(self, report_sha256):
        """Issue a fresh, unguessable challenge for evidence about report_sha256."""
        import secrets
        if type(report_sha256) is not str or len(report_sha256) != 64:
            raise ValueError("report_sha256 must be a 64-character hex digest")
        challenge = "maniac-" + secrets.token_hex(16)
        self._issued[challenge] = report_sha256
        return challenge

    def __call__(self, provenance):
        if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_FIELDS:
            return "HOLD: provenance must be exactly {'envelope'}; replay store is not request-selectable"
        if self._trust is None:
            return "HOLD: no pinned trusted keys configured"
        envelope = provenance["envelope"]
        try:
            challenge = envelope["record"]["challenge"]
            expected_sha256 = self._issued.pop(challenge)      # single-use
        except (KeyError, TypeError):
            return "HOLD: challenge was not issued by this verifier (or already used)"
        from shai_v31_bridge import evaluate
        return evaluate(envelope, db_path=self.replay_db, trust=self._trust,
                        expected_challenge=challenge, expected_sha256=expected_sha256)


def make_bridge_checker(replay_db, trust=None):
    """Provenance checker bound to ONE trusted replay database and pinned keys.
    Provenance must be exactly {"envelope": {"record": ...}}; a request that
    names its own "db_path", keys, hash or challenge is refused (144 HOLD)."""
    return BridgeChecker(replay_db, trust)


def no_trusted_replay_store(provenance):
    """Default: no replay store configured -> provenance can never pass."""
    return "HOLD: no trusted replay store configured"


def check_evidence(bundle, clock, provenance_checker=no_trusted_replay_store,
                   max_age=MAX_AGE, tolerance=TOLERANCE):
    """Run all four checks. Every problem is collected; any problem = HOLD."""
    reasons, audit = [], []
    try:
        if not isinstance(bundle, dict):
            reasons.append((G_RECEIVE, "evidence bundle is not a dict"))
            return EvidenceResult(HOLD, reasons, audit)
        unknown = set(bundle) - ALLOWED_FIELDS
        missing = ALLOWED_FIELDS - set(bundle)
        if unknown or missing:
            reasons.append((G_RECEIVE, "unknown %s / missing %s fields"
                            % (sorted(unknown), sorted(missing))))
            return EvidenceResult(HOLD, reasons, audit)
        now = clock()
        if not is_real_number(now):
            raise ValueError("clock must be a finite number")
        if not is_real_number(max_age) or max_age < 0:
            raise ValueError("max_age must be a finite nonnegative number")
        if not is_real_number(tolerance) or tolerance < 0:
            raise ValueError("tolerance must be a finite nonnegative number")
        _check_sensors(bundle["sensors"], now, max_age, tolerance, reasons, audit)
        _check_permissions(bundle["action"], bundle["consent"], now, reasons, audit)
        _check_provenance(bundle["provenance"], provenance_checker, reasons, audit)
    except Exception as exc:  # anything unexpected fails closed
        reasons.append((G_RECEIVE, "internal error: %s" % type(exc).__name__))
    overall = HOLD if reasons else PASS
    audit.append("CHECK EVIDENCE: %s" % overall)
    return EvidenceResult(overall, reasons, audit)


def _check_sensors(sensors, now, max_age, tolerance, reasons, audit):
    audit.append(G_OBSERVE_RAW + ": sensor validity checked")
    if not isinstance(sensors, list) or not sensors:
        reasons.append((G_OBSERVE_RAW, "no sensor readings"))
        return
    by_quantity = {}                          # quantity -> {source: value}
    for s in sensors:
        if not isinstance(s, dict):
            reasons.append((G_OBSERVE_RAW, "sensor reading is not a dict"))
            continue
        name = s.get("source")
        nums = [s.get(k) for k in ("value", "min", "max", "timestamp")]
        # bool is a kind of int in Python, so reject it explicitly
        if not all(is_real_number(n) for n in nums):
            reasons.append((G_OBSERVE_RAW, "sensor %r: non-numeric, NaN or inf" % (name,)))
            continue
        value, lo, hi, ts = nums
        if not lo <= value <= hi:
            reasons.append((G_OBSERVE_RAW, "sensor %r out of range" % (name,)))
            continue
        if ts > now or now - ts > max_age:
            reasons.append((G_OBSERVE_RAW, "sensor %r stale or from the future" % (name,)))
            continue
        # Stuck sensor: optional "history" of recent values (oldest first).
        # If the last STUCK_COUNT values are all identical, the sensor is stuck.
        history = s.get("history", [])
        if not isinstance(history, list):
            reasons.append((G_OBSERVE_RAW, "sensor %r: history is not a list" % (name,)))
            continue
        recent = history[-STUCK_COUNT:]
        if len(recent) == STUCK_COUNT and len(set(map(repr, recent))) == 1:
            reasons.append((G_OBSERVE_RAW, "sensor %r stuck (same value %d times)" % (name, STUCK_COUNT)))
            continue
        by_quantity.setdefault(s.get("quantity"), {})[name] = value

    audit.append(G_TRIANGULATE + ": contradictions checked")
    for quantity, readings in by_quantity.items():
        if len(readings) < 2:
            reasons.append((G_TRIANGULATE, "%r has fewer than two valid sources" % (quantity,)))
            continue
        if relative_spread(list(readings.values())) > tolerance:
            reasons.append((G_TRIANGULATE, "sources contradict on %r" % (quantity,)))


def _check_permissions(action, consent, now, reasons, audit):
    audit.append(G_VERIFY + ": consent scope checked")
    if not isinstance(consent, dict):
        reasons.append((G_VERIFY, "consent missing"))
        return
    expires = consent.get("expires_at")
    if not is_real_number(expires) or now >= expires:
        reasons.append((G_VERIFY, "consent expired or has no expiry"))
    allowed = consent.get("allowed_actions")
    # deny by default: only actions explicitly listed are allowed
    if not isinstance(allowed, list) or not isinstance(action, str) or action not in allowed:
        reasons.append((G_VERIFY, "action %r not inside human consent" % (action,)))


def _check_provenance(provenance, checker, reasons, audit):
    audit.append(G_RECEIVE + ": provenance checked")
    try:
        verdict = checker(provenance) if checker is not None else None
    except Exception:
        verdict = None
    if verdict != "REVIEW_REQUIRED":       # exactly this string, nothing else
        reasons.append((G_RECEIVE, "provenance failed (verdict %r)" % (verdict,)))
