"""SHAI digital twin - a simple simulated humanoid (software only).

NOT HARDWARE-READY. No motors, serial ports or network. ALL joint limits,
speeds, torques and energy costs below are ILLUSTRATIVE EXAMPLE VALUES,
not engineering specs.

The ONLY way to move a joint is request_motion(). It moves the simulated
joints only when ALL of these hold:
  1. the plan is valid and inside every joint's angle / speed / torque limit
  2. the battery has enough energy ABOVE the safe-stop reserve
  3. MANIAC run_loop() ends BALANCED with HUMAN_REVIEW
  4. a valid human "APPROVED" decision was recorded for THIS exact plan:
     the approval carries plan_sha256 = plan_digest(plan) (a canonical hash
     of request_id + moves + duration_s), re-checked right before motion,
     and each approval is single-use
Anything else -> 144 HOLD (or SAFE_LOCK) and nothing moves.
"""
from collections import deque
from dataclasses import dataclass
import copy
import hashlib
import json
import math
import random

from maniac.loop import run_loop
from maniac.monitor import Monitor
from maniac.supervisor import Supervisor
from maniac.triangulate import readings_from_bundle
from shai.power import PowerModel, _finite_number

HEIGHT_CM = 170
DT = 0.1                        # maximum simulation timestep (seconds)
TORQUE_NM_PER_DEG_S = 0.25      # example: estimated torque per deg/s of speed
WALL_DISTANCE_M = 2.0           # the twin stands 2 m from a wall
SAFE_STOP_WH = 1.0              # example energy a safe stop needs (from reserve)
MAX_TILT_DEG = 15.0             # IMU tilt above this -> fault

# ---- EXAMPLE joint table (illustrative only, NOT engineering specs) ----
#  name: (min deg, max deg, max deg/s, max torque Nm, Wh per degree)
JOINTS = {
    "neck_pitch":     (-30, 30, 30, 8, 0.002),
    "shoulder_left":  (-90, 90, 60, 40, 0.010),
    "shoulder_right": (-90, 90, 60, 40, 0.010),
    "elbow_left":     (0, 140, 90, 25, 0.006),
    "elbow_right":    (0, 140, 90, 25, 0.006),
    "hip_left":       (-30, 90, 45, 80, 0.020),
    "hip_right":      (-30, 90, 45, 80, 0.020),
    "knee_left":      (0, 120, 60, 80, 0.020),
    "knee_right":     (0, 120, 60, 80, 0.020),
}
COMPONENTS = ["camera", "lidar", "imu", "encoders", "contact", "power"]
ACTION = "move_joints"
MOVED, HOLD, SAFE_LOCK = "MOVED", "144 HOLD", "SAFE_LOCK"


APPROVAL_FIELDS = {"request_id", "plan_sha256", "operator_id", "decision", "reason"}


def plan_digest(plan):
    """Canonical SHA-256 of the exact motion plan (request_id, moves, duration_s).
    A human approval must carry this value, so it authorises THIS plan only."""
    body = {"request_id": plan["request_id"], "moves": plan["moves"],
            "duration_s": plan["duration_s"]}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def approval_for(plan, operator_id, decision, reason):
    """Build the approval record a human reviewer signs off for one exact plan."""
    return {"request_id": plan["request_id"], "plan_sha256": plan_digest(plan),
            "operator_id": operator_id, "decision": decision, "reason": reason}


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


@dataclass(frozen=True)
class MotionResult:
    request_id: object
    outcome: str            # "MOVED", "144 HOLD" or "SAFE_LOCK"
    moved: bool
    reasons: tuple
    balance: object = None  # the MANIAC BalanceResult, if the loop ran

    @property
    def approval_granted(self):
        """The machine never approves. A human approval is in balance.human_decision."""
        return False


class ShaiTwin:
    """Simulated 170 cm humanoid. Internal state is private (leading _)."""

    def __init__(self, seed=0, soc=1.0, temp_c=25.0, consent_seconds=600.0, replay_db=None, trust=None):
        if not _finite_number(consent_seconds) or consent_seconds < 0:
            raise ValueError("consent_seconds must be a finite nonnegative number")
        self._clock = FakeClock()
        self._rng = random.Random(seed)                # seeded: same run every time
        self._angles = {name: 0.0 for name in JOINTS}  # every joint starts at 0
        self._power = PowerModel(soc=soc, temp_c=temp_c)
        self._monitor = Monitor(self._clock, COMPONENTS)
        self._supervisor = Supervisor(clock=self._clock, replay_db=replay_db, trust=trust)  # trusted config
        self._history = {s: deque(maxlen=5) for s in ("camera", "lidar")}
        self._dead = set()              # sensors that dropped out
        self._dropout_plan = None       # (sensor, step) - simulation fault hook
        self._executed = set()          # request ids already used
        self._used_approvals = set()    # (request_id, plan_sha256) approvals consumed
        self._stops = []                # why each safe stop happened
        self._consent_until = self._clock() + consent_seconds
        self._tick()

    # ---- read-only views ---------------------------------------------
    @property
    def joint_angles(self):
        return dict(self._angles)      # a COPY - editing it changes nothing

    @property
    def power(self):
        return {"soc": self._power.soc, "energy_wh": self._power.energy_wh,
                "temp_c": self._power.temp_c, "available_wh": self._power.available_for_tasks()}

    @property
    def safe_stops(self):
        return list(self._stops)

    @property
    def monitor_state(self):
        return self._monitor.snapshot()

    # ---- simulation fault hooks (never move anything) ----------------
    def inject_sensor_dropout(self, sensor, after_steps=3):
        """Simulation only: make `sensor` stop reporting part-way through the next motion."""
        self._dropout_plan = (sensor, int(after_steps))

    def issue_challenge(self, report_sha256):
        """Verifier-issued, single-use challenge that evidence must be signed over."""
        issue = getattr(self._supervisor.provenance_checker, "issue_challenge", None)
        if issue is None:
            raise ValueError("no trusted replay store / pinned keys configured")
        return issue(report_sha256)

    # ---- the ONLY way to move ------------------------------------------
    def request_motion(self, plan, approval=None, provenance=None, ethical_evidence=None):
        """plan: {"request_id": str, "moves": {joint: target_deg}, "duration_s": number}
        approval: {"request_id", "plan_sha256", "operator_id", "decision", "reason"}
            from a human; build with approval_for(plan, ...). Single-use.
        provenance: {"envelope": {"record": ...}} - V3.1 evidence signed over a
            challenge from issue_challenge(). The replay database and pinned
            keys are fixed by ShaiTwin(replay_db=..., trust=...); a request-
            supplied "db_path", keys, hash or challenge is refused (144 HOLD)."""
        rid = plan.get("request_id") if isinstance(plan, dict) else None
        try:
            plan = copy.deepcopy(plan)   # caller can't change the plan after approval checks
            problems, energy = self._check_plan(plan)
            if problems:
                return self._hold(rid, problems)
            if rid in self._executed:
                return self._hold(rid, ["request id already used"])

            # Human approval must be for THIS exact plan (request id + plan hash)
            digest = plan_digest(plan)
            human = None
            if approval is not None:
                if not self._approval_matches(approval, rid, digest):
                    return self._hold(rid, ["approval is for a different request or plan"])
                if (rid, digest) in self._used_approvals:
                    return self._hold(rid, ["approval already used"])
                human = (approval.get("operator_id"), approval.get("decision"), approval.get("reason"))

            self._tick()
            bundle = self._bundle(provenance)
            balance, _ = run_loop(self._supervisor, self._request(rid, plan, ethical_evidence, provenance),
                                  self._monitor, bundle, self._clock,
                                  expected_value=WALL_DISTANCE_M,
                                  fresh_readings=readings_from_bundle(self._bundle(None)),
                                  human=human, plan_sha256=digest)
            self._executed.add(rid)
            if human is not None:
                self._used_approvals.add((rid, digest))   # single-use, even if held
            problems += ["%s: %s" % tuple(r) for r in balance.reasons]
            if self._monitor.snapshot()["state"] == "SAFE_LOCK":
                return MotionResult(rid, SAFE_LOCK, False, tuple(problems), balance)
            if balance.status != "BALANCED" or balance.outcome != "HUMAN_REVIEW":
                return self._hold(rid, problems or ["MANIAC loop not balanced"], balance)
            if balance.human_decision is None or not balance.human_decision.approved:
                return self._hold(rid, problems + ["no human APPROVED decision for this request"], balance)
            # Re-check the binding right before motion
            if approval is None or not self._approval_matches(approval, rid, digest) \
                    or plan_digest(plan) != digest:
                return self._hold(rid, problems + ["approval does not match the exact plan"], balance)
            return self._execute(rid, plan, energy, balance)
        except Exception as exc:  # fail closed
            return self._hold(rid, ["internal error: %s" % type(exc).__name__])

    def safe_stop(self, why="safe stop"):
        """Bring every joint to rest where it is (no new motion), powered by the reserve."""
        self._power.draw_reserve(SAFE_STOP_WH)
        self._stops.append(why)
        return dict(self._angles)

    # ---- private helpers -------------------------------------------------
    @staticmethod
    def _approval_matches(approval, rid, digest):
        return (isinstance(approval, dict) and set(approval) == APPROVAL_FIELDS
                and type(approval["request_id"]) is str and approval["request_id"] == rid
                and type(approval["plan_sha256"]) is str and approval["plan_sha256"] == digest)

    def _check_plan(self, plan):
        """Returns (problems, energy_wh). Checks shape, limits and energy."""
        if not isinstance(plan, dict) or set(plan) != {"request_id", "moves", "duration_s"}:
            return ["plan must have exactly request_id, moves, duration_s"], 0.0
        rid, moves, secs = plan["request_id"], plan["moves"], plan["duration_s"]
        if type(rid) is not str or not rid.strip():
            return ["request_id must be text"], 0.0
        if type(secs) not in (int, float) or not 0 < secs <= 30:
            return ["duration_s must be a number from 0 to 30"], 0.0
        if self._clock() + secs > self._consent_until:
            return ["consent expires before motion completes"], 0.0
        if not isinstance(moves, dict) or not moves:
            return ["moves must name at least one joint"], 0.0
        problems, energy = [], self._power.motion_energy_wh(0, 0, secs)
        for joint, target in moves.items():
            if joint not in JOINTS:
                problems.append("unknown joint %r" % (joint,)); continue
            if type(target) not in (int, float) or target != target:
                problems.append("%s: target is not a number" % joint); continue
            lo, hi, max_speed, max_torque, wh_per_deg = JOINTS[joint]
            delta = target - self._angles[joint]
            speed = abs(delta) / secs
            if not lo <= target <= hi:
                problems.append("%s: %s° outside limit %s..%s°" % (joint, target, lo, hi))
            if speed > max_speed:
                problems.append("%s: %.0f°/s over max %s°/s" % (joint, speed, max_speed))
            if speed * TORQUE_NM_PER_DEG_S > max_torque:
                problems.append("%s: torque over %s Nm" % (joint, max_torque))
            energy += abs(delta) * wh_per_deg
        if energy > self._power.available_for_tasks():
            problems.append("not enough energy above the safe-stop reserve")
        return problems, energy

    def _execute(self, rid, plan, energy, balance):
        """Move in steps no longer than DT. Stop safely when a check fails."""
        start = dict(self._angles)
        started_at = self._clock()
        steps = max(1, math.ceil(plan["duration_s"] / DT))
        step_seconds = plan["duration_s"] / steps
        if not self._power.draw_task(energy):
            return self._hold(rid, ["energy check failed at start"], balance)
        for i in range(1, steps + 1):
            step_end = started_at + i * step_seconds
            if self._clock() >= self._consent_until or step_end > self._consent_until:
                self.safe_stop("consent expired before next motion step")
                return MotionResult(rid, HOLD, i > 1,
                                    ("consent expired before next motion step",), balance)
            if self._dropout_plan and self._dropout_plan[1] == i:
                self._dead.add(self._dropout_plan[0])
                self._dropout_plan = None
            for joint, target in plan["moves"].items():
                self._angles[joint] = start[joint] + (target - start[joint]) * i / steps
            self._clock.t = step_end
            self._power.cool(step_seconds)
            self._tick()
            snap = self._monitor.snapshot()
            if snap["state"] != "MONITOR":
                self.safe_stop(snap["reason"])
                outcome = SAFE_LOCK if snap["state"] == "SAFE_LOCK" else HOLD
                return MotionResult(rid, outcome, True,
                                    ("stopped mid-motion: %s" % snap["reason"],), balance)
        return MotionResult(rid, MOVED, True, (), balance)

    def _hold(self, rid, problems, balance=None):
        return MotionResult(rid, HOLD, False, tuple(problems), balance)

    def _tick(self):
        """Live sensors heartbeat, watchdog is kicked, power faults checked."""
        for c in COMPONENTS:
            if c not in self._dead:
                self._monitor.heartbeat(c)
        for c in self._dead:
            if "SENSOR_DROPOUT_" + c not in self._monitor.faults:
                self._monitor.raise_fault("SENSOR_DROPOUT_" + c, "%s stopped reporting" % c)
        self._monitor.kick()
        self._power.check(self._monitor)

    def sense(self):
        """All simulated sensors (seeded noise). Dead sensors return None."""
        now = self._clock()
        out = {}
        for src in ("camera", "lidar"):
            value = WALL_DISTANCE_M + self._rng.gauss(0, 0.004)
            self._history[src].append(round(value, 4))
            out[src] = None if src in self._dead else value
        out["imu_tilt_deg"] = None if "imu" in self._dead else abs(self._rng.gauss(0, 0.5))
        out["encoders"] = None if "encoders" in self._dead else dict(self._angles)
        out["contact"] = None if "contact" in self._dead else {"foot_left": True, "foot_right": True}
        out["temp_c"] = self._power.temp_c
        out["time"] = now
        return out

    def _bundle(self, provenance):
        """Evidence in the format maniac.evidence / triangulate expect."""
        s = self.sense()
        sensors = []
        for src in ("camera", "lidar"):
            if s[src] is not None:
                sensors.append({"source": src, "type": src, "quantity": "distance",
                                "value": s[src], "min": 0.1, "max": 10.0,
                                "timestamp": s["time"] - 0.05, "history": list(self._history[src])})
        return {"sensors": sensors, "action": ACTION,
                "consent": {"allowed_actions": [ACTION], "expires_at": self._consent_until},
                "provenance": provenance}

    def _request(self, rid, plan, ethical_evidence, provenance):
        """Supervisor request built from the plan and live sensors."""
        s = self.sense()
        fastest = max(abs(t - self._angles[j]) / plan["duration_s"] / JOINTS[j][2]
                      for j, t in plan["moves"].items())
        return {"request_id": rid, "action": ACTION,
                "requested_limits": {"speed_fraction": round(fastest, 4)},
                "consent": {"allowed_actions": [ACTION], "limits": {"speed_fraction": 1.0}},
                "sensors": [{"source": src, "value": s[src], "min": 0.1, "max": 10.0}
                            for src in ("camera", "lidar") if s[src] is not None],
                "heartbeats": [self._clock() - 0.05], "faults": [],
                # This field only says signed evidence was SUPPLIED. The real V3.1
                # signature + replay check runs in CHECK EVIDENCE via the bridge.
                "evidence_verdict": "REVIEW_REQUIRED" if provenance else None,
                "ethical_evidence": ethical_evidence}

