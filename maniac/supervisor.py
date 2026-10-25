"""MANIAC supervisor core (offline simulation only - controls no hardware).

Flow (Mitch's design):
HUMAN (purpose, values, consent) -> SYNTH_SHAI AI cognition engine
-> USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1)
-> 000 PAUSE / ASSESS -> 111 IDENTIFY INTENT -> 222 OBSERVE RAW
-> 333 DEFINE PROBLEM -> 333000 RECORD -> 777000 RECEIVE EVIDENCE
-> 555000 TRIANGULATE -> 888000 CHECK LOOP -> CONSEQUENCE REVIEW
   RISK / ERROR FOUND  -> 144 HOLD -> 1301133 REPAIR -> 666000 RECOVERY
   EVIDENCE SUFFICIENT -> 444000 VERIFY -> HUMAN REVIEW
both -> 222000 RE-OBSERVE -> 111000 COMPARE / LEARN -> 999000 AUDIT -> Δ BALANCE

The supervisor can only ever answer "144 HOLD" or "HUMAN_REVIEW".
approval_granted is always False: only a human can approve.
"""

from dataclasses import dataclass, field, replace
from enum import Enum
import hashlib
import json
import math

HOLD = "144 HOLD"
HUMAN_REVIEW = "HUMAN_REVIEW"


class Gate(Enum):
    PAUSE = "000 PAUSE / ASSESS"
    IDENTIFY = "111 IDENTIFY INTENT"
    OBSERVE_RAW = "222 OBSERVE RAW"
    DEFINE = "333 DEFINE PROBLEM"
    RECORD = "333000 RECORD"
    COMPARE_LEARN = "111000 COMPARE / LEARN"
    RE_OBSERVE = "222000 RE-OBSERVE"
    TRIANGULATE = "555000 TRIANGULATE"
    RECOVERY = "666000 RECOVERY"
    RECEIVE_EVIDENCE = "777000 RECEIVE EVIDENCE"
    CHECK_LOOP = "888000 CHECK LOOP"
    AUDIT = "999000 AUDIT"
    REPAIR = "1301133 BUILD / REPAIR / REFRAME"
    VERIFY = "444000 VERIFY / HUMAN APPROVAL"
    HOLD = "144 HOLD"
    BALANCE = "Δ BALANCE"


# Named layers (not numbered gates) recorded in the audit trail.
USHAI_CONSCIENCE = "USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1)"
CONSEQUENCE_REVIEW = "CONSEQUENCE REVIEW"

ALLOWED_FIELDS = {
    "request_id", "action", "requested_limits", "consent", "sensors",
    "heartbeats", "faults", "evidence_verdict", "ethical_evidence",
}
REQUIRED_FIELDS = ALLOWED_FIELDS - {"faults"}


class HoldError(Exception):
    """Raised inside the walk; always turned into 144 HOLD."""


@dataclass(frozen=True)   # frozen: fields can't be changed after creation
class Result:
    request_id: object
    decision: str
    reason: str
    audit: list = field(default_factory=list)

    @property
    def approval_granted(self):
        """Always False. A read-only property, so it can never be set to True."""
        return False


def ushai_conscience_check(evidence):
    """USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1) - Mitch's gate in
    ushai_catharsis.py. Returns None if it says REVIEW_REQUIRED, else a
    HOLD reason. It can only stop things, never approve them."""
    from ushai_catharsis import USHAICatharsis, State
    gate = USHAICatharsis()
    if gate.assess(evidence) != State.REVIEW.value:
        return "USHAI conscience: " + gate.reason
    return None


class Supervisor:
    def __init__(self, clock, heartbeat_timeout=2.0, tolerance=0.05, replay_db=None):
        self.clock = clock                      # injectable: () -> float seconds
        # Trusted configuration: the ONE V3.1 replay database used by CHECK
        # EVIDENCE. Requests cannot choose it. None -> provenance always HOLDs.
        from maniac.evidence import make_bridge_checker, no_trusted_replay_store
        self.provenance_checker = (no_trusted_replay_store if replay_db is None
                                   else make_bridge_checker(replay_db))
        self.heartbeat_timeout = heartbeat_timeout
        self.tolerance = tolerance              # max relative disagreement
        self._seen = set()                      # fingerprints (CHECK LOOP)
        self._held_ids = set()                  # request ids that ended in HOLD

    # ---------------------------------------------------------------
    def evaluate(self, request, monitor_snapshot=None, evidence_result=None):
        """monitor_snapshot (optional): Monitor.snapshot(); anything but
        state MONITOR means 144 HOLD.
        evidence_result (optional): maniac.evidence.check_evidence() result;
        anything but overall PASS means 144 HOLD."""
        audit = []
        rid = request.get("request_id") if isinstance(request, dict) else None
        try:
            reason = self._walk(request, audit, monitor_snapshot, evidence_result)
            if reason is None:
                audit.append(CONSEQUENCE_REVIEW + ": EVIDENCE SUFFICIENT")
                audit.append(Gate.VERIFY.value)
                decision, reason = HUMAN_REVIEW, "evidence sufficient; a human must decide"
            else:
                audit.append(CONSEQUENCE_REVIEW + ": RISK / ERROR FOUND")
                decision = HOLD
        except Exception as exc:  # fail closed on anything unexpected
            decision, reason = HOLD, "internal error: %s" % type(exc).__name__
        if decision == HOLD:
            audit.append(Gate.HOLD.value)
            if rid is not None:
                try:
                    self._held_ids.add(rid)
                except TypeError:
                    pass
        # Post-decision gates: recorded only, never change the decision.
        audit += [Gate.RE_OBSERVE.value, Gate.COMPARE_LEARN.value,
                  Gate.AUDIT.value, Gate.BALANCE.value]
        return Result(rid, decision, reason, audit)

    def review(self, request, monitor_snapshot, evidence_result, triangulation):
        """Full 444000 VERIFY / CONSEQUENCE REVIEW: runs evaluate() and then
        collects reasons from EVERY layer (USHAI, monitor, evidence,
        triangulate, supervisor). Returns a maniac.verify.VerifyResult."""
        from maniac.verify import consequence_review
        from ushai_catharsis import USHAICatharsis
        ushai = USHAICatharsis()
        ushai.assess(request.get("ethical_evidence") if isinstance(request, dict) else None)
        result = self.evaluate(request, monitor_snapshot, evidence_result)
        return consequence_review(ushai, monitor_snapshot, evidence_result, triangulation, result)

    def recover(self, held, new_request):
        """1301133 REPAIR + 666000 RECOVERY: re-evaluate only with a fresh
        request id that has never been held. Never re-uses the held one."""
        if held.decision != HOLD:
            return Result(new_request.get("request_id") if isinstance(new_request, dict) else None,
                          HOLD, "recover() only applies to a held result",
                          [Gate.REPAIR.value, Gate.HOLD.value])
        nid = new_request.get("request_id") if isinstance(new_request, dict) else None
        if not isinstance(nid, str) or not nid.strip() or nid == held.request_id or nid in self._held_ids:
            return Result(nid, HOLD, "recovery needs a new request id and fresh evidence",
                          [Gate.REPAIR.value, Gate.RECOVERY.value, Gate.HOLD.value])
        result = self.evaluate(new_request)
        # Result is frozen, so build a new one with the repair steps in front
        return replace(result, audit=[Gate.REPAIR.value, Gate.RECOVERY.value] + result.audit)

    # ---------------------------------------------------------------
    def _walk(self, req, audit, monitor_snapshot=None, evidence_result=None):
        """Return None if everything passed, else the HOLD reason."""
        def fail(msg):
            raise HoldError(msg)
        try:
            if not isinstance(req, dict):
                fail("request is not a dict")
            audit.append(USHAI_CONSCIENCE)
            concern = ushai_conscience_check(req.get("ethical_evidence"))
            if concern:
                fail(concern)
            audit.append(Gate.PAUSE.value)
            unknown = set(req) - ALLOWED_FIELDS
            if unknown:
                fail("unknown field(s): %s" % ", ".join(sorted(map(str, unknown))))
            missing = REQUIRED_FIELDS - set(req)
            if missing:
                fail("missing field(s): %s" % ", ".join(sorted(missing)))

            audit.append(Gate.IDENTIFY.value)
            if not isinstance(req["request_id"], str) or not req["request_id"].strip():
                fail("request id must be a non-empty string")
            action = req["action"]
            if not isinstance(action, str) or not action:
                fail("action must be a non-empty string")
            consent = req["consent"]
            if not isinstance(consent, dict):
                fail("consent must be a dict")

            audit.append(Gate.OBSERVE_RAW.value)
            sensors = req["sensors"]
            if not isinstance(sensors, list):
                fail("sensors must be a list")

            audit.append(Gate.DEFINE.value)
            limits = req["requested_limits"]
            if not isinstance(limits, dict):
                fail("requested_limits must be a dict")

            audit.append(Gate.RECORD.value)
            fingerprint = hashlib.sha256(
                json.dumps(req, sort_keys=True, default=str).encode()).hexdigest()

            audit.append(Gate.RECEIVE_EVIDENCE.value)
            if req["evidence_verdict"] != "REVIEW_REQUIRED":
                fail("provenance failed or missing (evidence verdict %r)" % (req["evidence_verdict"],))

            # MONITOR SYSTEM: heartbeat / watchdog / faults
            if monitor_snapshot is not None:
                if not isinstance(monitor_snapshot, dict) or monitor_snapshot.get("state") != "MONITOR":
                    state = monitor_snapshot.get("state") if isinstance(monitor_snapshot, dict) else None
                    why = monitor_snapshot.get("reason") if isinstance(monitor_snapshot, dict) else "bad snapshot"
                    fail("monitor state %s: %s" % (state, why))
            now = self.clock()
            if type(now) not in (int, float) or not math.isfinite(now):
                fail("invalid clock")
            beats = req["heartbeats"]
            if not isinstance(beats, list) or not beats:
                fail("no heartbeat")
            if any(type(b) not in (int, float) or not math.isfinite(b) for b in beats):
                fail("invalid heartbeat")
            last = max(beats)
            if last > now or now - last > self.heartbeat_timeout:
                fail("watchdog: heartbeat missed or from the future")
            if req.get("faults"):
                fail("active fault(s): %s" % req["faults"])

            # CHECK EVIDENCE module (optional): must be a real PASS result
            if evidence_result is not None:
                from maniac.evidence import EvidenceResult, PASS
                if not isinstance(evidence_result, EvidenceResult) or evidence_result.overall != PASS:
                    why = getattr(evidence_result, "reasons", "bad evidence result")
                    fail("CHECK EVIDENCE: %s" % (why,))

            # CHECK EVIDENCE: consent / permissions
            if action not in consent.get("allowed_actions", []):
                fail("action %r is outside human consent" % action)
            caps = consent.get("limits", {})
            for name, value in limits.items():
                if (name not in caps or type(value) not in (int, float)
                        or type(caps[name]) not in (int, float)
                        or not math.isfinite(value) or not math.isfinite(caps[name])
                        or value < 0 or caps[name] < 0 or value > caps[name]):
                    fail("limit %r outside consent" % name)

            # CHECK EVIDENCE: sensor validity
            values, sources = [], set()
            for s in sensors:
                if not isinstance(s, dict) or any(type(s.get(k)) not in (int, float) or not math.isfinite(s[k]) for k in ("value", "min", "max")):
                    fail("invalid sensor measurement")
                v, lo, hi = s["value"], s["min"], s["max"]
                if not lo <= v <= hi:
                    fail("sensor %r out of range" % s["source"])
                values.append(v)
                sources.add(s["source"])

            audit.append(Gate.TRIANGULATE.value)
            if len(sources) < 2:
                fail("fewer than two independent sources")
            spread = max(values) - min(values)
            scale = max(abs(v) for v in values) or 1.0
            if spread / scale > self.tolerance:
                fail("contradiction between sources beyond tolerance")

            audit.append(Gate.CHECK_LOOP.value)
            if fingerprint in self._seen:
                fail("repeated identical request (loop)")
            self._seen.add(fingerprint)
            return None
        except HoldError as e:
            return str(e)
