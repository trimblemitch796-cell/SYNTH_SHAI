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
from maniac.supervisor import Supervisor
from maniac.triangulate import triangulate, readings_from_bundle
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
            "provenance": {"envelope": signed_envelope("maniac-simulation-challenge-" + name), "db_path": db_path},
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
        self.supervisor = Supervisor(clock=self.clock)

    def run(self):
        """Monitor -> CHECK EVIDENCE -> 555000 TRIANGULATE -> 444000 VERIFY.
        Returns (outcome, reason). The reason lists EVERY layer's problems."""
        snap = self.monitor.snapshot()
        if snap["state"] == SAFE_LOCK:
            return SAFE_LOCK, snap["reason"]
        evidence = check_evidence(self.bundle, self.clock)
        tri = triangulate(readings_from_bundle(self.bundle))
        result = self.supervisor.review(self.request, snap, evidence, tri)
        assert result.approval_granted is False   # never, in any scenario
        reason = "; ".join("%s: %s" % pair for pair in result.reasons) or "evidence sufficient"
        return result.decision, reason


# ---- fault injectors: each one changes the clean scenario --------------
def cam(s):
    return s.bundle["sensors"][0]


def replay(s):
    # Use the evidence once (accepted), then submit the very same evidence again
    check_evidence(copy.deepcopy(s.bundle), s.clock)


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
    print("%-24s %-32s %-13s %-13s %s" % ("SCENARIO", "INJECTED FAULT", "EXPECTED", "ACTUAL", "RESULT"))
    for r in report:
        print("%-24s %-32s %-13s %-13s %s" % (r["name"], r["fault"], r["expected"],
                                              r["actual"], "pass" if r["passed"] else "FAIL"))
    failed = [r for r in report if not r["passed"]]
    print("\n%d/%d scenarios passed. Offline simulation only - no hardware." %
          (len(report) - len(failed), len(report)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
