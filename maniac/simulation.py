"""MANIAC_SIMULATION - offline synthetic fault testing.

Builds fake scenarios and pushes each one through the REAL modules:
    Monitor -> check_evidence (with the real V3.1 bridge) -> Supervisor
Offline simulation only: no hardware, no network, no real sleeps.
Keys are made from fixed seeds, so every run gives the same results.

Run it:  python3 -m maniac.simulation
"""
import copy
import hashlib
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from maniac.monitor import Monitor
from maniac.evidence import check_evidence
from maniac.chain import run_chain
from maniac.loop import run_loop
from maniac.supervisor import Supervisor
from maniac.triangulate import readings_from_bundle
from ushai_catharsis import EthicalEvidence
from verification_v3 import canonical_bytes, sha256_text

NOW = 1000.0
HOLD, SAFE_LOCK, REVIEW = "144 HOLD", "SAFE_LOCK", "HUMAN_REVIEW"


class FakeClock:
    """A clock we move by hand. No real time is used."""
    def __init__(self, t=NOW):
        self.t = t

    def __call__(self):
        return self.t


def signed_envelope(challenge, report="Offline only: no actuation"):
    """Two V3.1 evidence signatures made from fixed (seeded) keys."""
    revision, digest = "sim-rev", sha256_text(report)
    trusted, evidence = {}, []
    for i in range(2):
        seed = hashlib.sha256(b"maniac-sim-key-%d" % i).digest()
        private = Ed25519PrivateKey.from_private_bytes(seed)
        public = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        item = {"source_id": "source-%d" % i, "key_id": "key-%d" % i,
                "source_revision": revision, "report_sha256": digest, "challenge": challenge}
        trusted[item["key_id"]] = {"source_id": item["source_id"], "public_key_hex": public.hex()}
        evidence.append({**item, "signature": private.sign(canonical_bytes(item)).hex()})
    return {"record": {"test_report": report, "source_revision": revision,
                       "challenge": challenge, "verification_evidence": evidence},
            "trusted_keys": trusted, "expected_sha256": digest, "expected_challenge": challenge}


class Scenario:
    """Everything one run needs. Each fault function changes one part."""
    def __init__(self, name, db_path):
        self.name = name
        self.clock = FakeClock()
        self.monitor = Monitor(self.clock, ["camera", "lidar"])
        for c in ("camera", "lidar"):
            self.monitor.heartbeat(c)
        self.monitor.kick()
        self.bundle = {
            "sensors": [
                {"source": "camera", "type": "camera", "quantity": "distance", "value": 10.0, "min": 0, "max": 100,
                 "timestamp": NOW - 0.5, "history": [9.6, 9.8, 9.9, 10.1, 10.0]},
                {"source": "lidar", "type": "lidar", "quantity": "distance", "value": 10.2, "min": 0, "max": 100,
                 "timestamp": NOW - 0.5, "history": [9.7, 9.9, 10.0, 10.3, 10.2]},
            ],
            "action": "move_arm",
            "consent": {"allowed_actions": ["move_arm"], "expires_at": NOW + 60},
            "provenance": {"envelope": signed_envelope("maniac-simulation-challenge-" + name)},
        }
        self.request = {
            "request_id": "sim-" + name,
            "action": "move_arm",
            "requested_limits": {"speed": 0.5},
            "consent": {"allowed_actions": ["move_arm"], "limits": {"speed": 1.0}},
            "sensors": [{"source": "camera", "value": 10.0, "min": 0, "max": 100},
                        {"source": "lidar", "value": 10.2, "min": 0, "max": 100}],
            "heartbeats": [NOW - 0.5],
            "faults": [],
            "evidence_verdict": "REVIEW_REQUIRED",
            "ethical_evidence": EthicalEvidence(True, True, True, False, False, True),
        }
        self.supervisor = Supervisor(clock=self.clock, replay_db=db_path)
        self.db_path = db_path
        self.loop = None          # set by a loop scenario to run the whole loop
        self.twin_case = None     # set by a SHAI twin scenario

    def run_full_loop(self):
        """Whole loop: chain -> (HOLD -> REPAIR -> RECOVERY) -> 222000 -> 111000 -> 999000 -> Δ."""
        result, _ = run_loop(self.supervisor, self.request, self.monitor, self.bundle, self.clock,
                             expected_value=10.1,
                             fresh_readings=self.loop.get("fresh", readings_from_bundle(self.bundle)),
                             recovery=self.loop.get("recovery"))
        assert result.approval_granted is False
        reason = "; ".join("%s: %s" % tuple(r) for r in result.reasons) or "balanced"
        return result.outcome, "%s - %s" % (result.status, reason)

    def run(self):
        """Monitor -> CHECK EVIDENCE -> 555000 TRIANGULATE -> 444000 VERIFY.
        Returns (outcome, reason). The reason lists EVERY layer's problems."""
        if self.twin_case is not None:
            return self.twin_case(self)
        if self.loop is not None:
            return self.run_full_loop()
        if self.monitor.snapshot()["state"] == SAFE_LOCK:
            return SAFE_LOCK, self.monitor.snapshot()["reason"]
        result = run_chain(self.supervisor, self.request, self.monitor, self.bundle, self.clock)
        assert result.approval_granted is False   # never, in any scenario
        reason = "; ".join("%s: %s" % pair for pair in result.reasons) or "evidence sufficient"
        return result.decision, reason


# ---- fault injectors: each one changes the clean scenario --------------
def cam(s):
    return s.bundle["sensors"][0]


def replay(s):
    # Use the evidence once (accepted), then submit the very same evidence again
    check_evidence(copy.deepcopy(s.bundle), s.clock, provenance_checker=s.supervisor.provenance_checker)


def tamper(s):
    s.bundle["provenance"]["envelope"]["record"]["test_report"] = "edited after signing"


def forge(s):
    sig = s.bundle["provenance"]["envelope"]["record"]["verification_evidence"][0]
    sig["signature"] = "00" * 64


def dead_heartbeat(s):
    s.clock.t += 3            # 3 s pass; only the watchdog and lidar keep going
    s.monitor.kick()
    s.monitor.heartbeat("lidar")
    _refresh(s)


def watchdog_timeout(s):
    s.clock.t += 3            # heartbeats keep coming but nobody kicks
    for c in ("camera", "lidar"):
        s.monitor.heartbeat(c)
    _refresh(s)


def _refresh(s):
    """After moving the clock, make the other evidence fresh again so only
    the injected fault is wrong."""
    for sensor in s.bundle["sensors"]:
        sensor["timestamp"] = s.clock.t - 0.5
    s.bundle["consent"]["expires_at"] = s.clock.t + 60
    s.request["heartbeats"] = [s.clock.t - 0.5]


def repeated_fault(s):
    for _ in range(3):
        s.monitor.raise_fault("slip")
        s.monitor.clear_fault("slip", "retry")


def several(s):
    cam(s)["value"] = float("nan")
    s.bundle["action"] = "open_door"
    s.monitor.raise_fault("overheat")


# (name, injected fault description, injector, expected outcome)
def loop_clean(s):
    s.loop = {}


def _held_then_recover(s, fresh_challenge, fresh_time):
    """First pass held by a NaN reading; then a repair + recovery attempt."""
    cam(s)["value"] = float("nan")
    s.clock.t += 1.0                      # time moves on during the repair
    for c in ("camera", "lidar"):
        s.monitor.heartbeat(c)
    s.monitor.kick()
    new = copy.deepcopy(s.bundle)
    new["sensors"][0]["value"] = 10.0
    for sensor in new["sensors"]:
        sensor["timestamp"] = fresh_time(s)
    if fresh_challenge:
        new["provenance"]["envelope"] = signed_envelope("maniac-simulation-recovery-" + s.name)
    req = dict(s.request, request_id=s.request["request_id"] + "-recovered",
               heartbeats=[s.clock.t - 0.2])
    s.loop = {"recovery": {"repair_note": {"operator_id": "mitch", "reason": "replaced camera"},
                           "request": req, "bundle": new},
              "fresh": readings_from_bundle(new)}     # the world after the repair


# ---- SHAI digital twin scenarios (software only, no hardware) ---------
MOVED = "MOVED"
GOOD_ETHICS = EthicalEvidence(True, True, True, False, False, True)


def twin(kind):
    """Build a twin scenario. Returns the injector used in SCENARIOS."""
    def inject(s):
        def run(s):
            from shai.twin import ShaiTwin, approval_for            # imported here: shai imports maniac
            kw = {"soc": 0.10} if kind == "low_battery" else {}
            kw.update({"temp_c": 65.0} if kind == "overheat" else {})
            t = ShaiTwin(seed=7, replay_db=s.db_path, **kw)
            before = t.joint_angles
            rid = "twin-" + kind
            target = 200 if kind == "over_limit" else 30
            plan = {"request_id": rid, "moves": {"elbow_left": target}, "duration_s": 2.0}
            approval = approval_for(plan, "mitch", "APPROVED", "small elbow test")
            if kind == "unapproved":
                approval = None
            if kind == "replayed_approval":
                approval = dict(approval, request_id="twin-some-other-request")
            if kind == "dropout":
                t.inject_sensor_dropout("lidar", after_steps=5)
            prov = {"envelope": signed_envelope("maniac-twin-challenge-" + kind)}
            r = t.request_motion(plan, approval, prov, GOOD_ETHICS)
            assert r.approval_granted is False
            moved = t.joint_angles != before
            if r.outcome != MOVED and kind != "dropout":
                assert not moved, "joint moved without full approval"
            if kind == "dropout":
                assert t.safe_stops, "no safe stop after dropout"
            return r.outcome, "; ".join(r.reasons) or "moved %s" % t.joint_angles["elbow_left"]
        s.twin_case = run
    return inject


SCENARIOS = [
    ("baseline", "none (clean)", lambda s: None, REVIEW),
    ("dead_heartbeat", "camera heartbeat stops", dead_heartbeat, HOLD),
    ("watchdog_timeout", "watchdog not kicked for 3 s", watchdog_timeout, HOLD),
    ("stuck_sensor", "camera reports 10.0 five times", lambda s: cam(s).update(history=[10.0] * 5), HOLD),
    ("out_of_range", "camera value 500 (max 100)", lambda s: cam(s).update(value=500.0), HOLD),
    ("nan_reading", "camera value NaN", lambda s: cam(s).update(value=float("nan")), HOLD),
    ("inf_reading", "camera value inf", lambda s: cam(s).update(value=float("inf")), HOLD),
    ("stale_reading", "camera reading 5 s old", lambda s: cam(s).update(timestamp=NOW - 5), HOLD),
    ("contradiction", "camera 10.0 vs lidar 20.0", lambda s: s.bundle["sensors"][1].update(value=20.0), HOLD),
    ("single_source", "lidar missing", lambda s: s.bundle["sensors"].pop(), HOLD),
    ("missing_consent", "no consent", lambda s: s.bundle.update(consent=None), HOLD),
    ("expired_consent", "consent expired", lambda s: s.bundle["consent"].update(expires_at=NOW - 1), HOLD),
    ("action_outside_consent", "action open_door", lambda s: s.bundle.update(action="open_door"), HOLD),
    ("forged_provenance", "signature replaced", forge, HOLD),
    ("tampered_provenance", "report edited after signing", tamper, HOLD),
    ("replayed_evidence", "same evidence used twice", replay, HOLD),
    ("malformed_input", "sensors is a string", lambda s: s.bundle.update(sensors="lots"), HOLD),
    ("same_type_sources", "two cameras (same type)",
     lambda s: s.bundle["sensors"][1].update(type="camera"), HOLD),
    ("repeated_fault", "fault 'slip' raised 3 times", repeated_fault, SAFE_LOCK),
    ("several_faults", "NaN + wrong action + overheat", several, HOLD),
    ("loop_clean", "none: full loop", loop_clean, REVIEW),
    ("loop_recovery_fresh", "NaN, then repair + fresh evidence",
     lambda s: _held_then_recover(s, True, lambda s: s.clock.t - 0.2), REVIEW),
    ("loop_recovery_replayed", "NaN, then repair re-using old challenge",
     lambda s: _held_then_recover(s, False, lambda s: s.clock.t - 0.2), HOLD),
    ("loop_recovery_stale", "NaN, then repair with old readings",
     lambda s: _held_then_recover(s, True, lambda s: NOW - 0.5), HOLD),
    ("loop_no_recovery", "NaN, no repair attempted",
     lambda s: (cam(s).update(value=float("nan")), loop_clean(s)), HOLD),
    ("twin_approved_motion", "SHAI twin: approved 30° elbow move", twin("approved"), MOVED),
    ("twin_unapproved", "SHAI twin: no human approval", twin("unapproved"), HOLD),
    ("twin_over_limit", "SHAI twin: elbow to 200° (max 140)", twin("over_limit"), HOLD),
    ("twin_low_battery", "SHAI twin: battery at 10%", twin("low_battery"), HOLD),
    ("twin_overheat", "SHAI twin: pack at 65 °C", twin("overheat"), SAFE_LOCK),
    ("twin_sensor_dropout", "SHAI twin: lidar drops out mid-motion", twin("dropout"), HOLD),
    ("twin_replayed_approval", "SHAI twin: approval for another request", twin("replayed_approval"), HOLD),
    ("loop_reobserve_mismatch", "world moved after decision (30.0 seen)",
     lambda s: (loop_clean(s), s.loop.update(fresh=[
         {"source_id": "camera", "source_type": "camera", "value": 30.0},
         {"source_id": "lidar", "source_type": "lidar", "value": 30.1}])), HOLD),
]


def run_all():
    """Run every scenario. Returns a list of report dicts."""
    report = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, fault, inject, expected in SCENARIOS:
            s = Scenario(name, str(Path(tmp) / (name + ".sqlite")))
            try:
                inject(s)
                actual, reason = s.run()
            except Exception as exc:       # a crash is a failed scenario
                actual, reason = "ERROR", repr(exc)
            report.append({"name": name, "fault": fault, "expected": expected,
                           "actual": actual, "reason": reason, "passed": actual == expected})
    return report


def main():
    report = run_all()
    print("%-24s %-42s %-13s %-13s %s" % ("SCENARIO", "INJECTED FAULT", "EXPECTED", "ACTUAL", "RESULT"))
    for r in report:
        print("%-24s %-42s %-13s %-13s %s" % (r["name"], r["fault"], r["expected"],
                                              r["actual"], "pass" if r["passed"] else "FAIL"))
    failed = [r for r in report if not r["passed"]]
    print("\n%d/%d scenarios passed. Offline simulation only - no hardware." %
          (len(report) - len(failed), len(report)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
