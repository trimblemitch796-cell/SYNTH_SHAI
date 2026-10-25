"""Fair comparison benchmark (offline simulation only - no hardware).

Runs every maniac.simulation scenario through three approaches:

  SYNTH_SHAI  - the repository's own loop, unchanged (maniac.simulation.run_all).
  BASELINE_A  - conventional emergency stop + watchdog (see baseline_a()).
  BASELINE_B  - plain human-approval gate (see baseline_b()).

Each outcome is reduced to ALLOW or STOP and scored against the scenario's
existing expected outcome (REVIEW/MOVED = safe to allow, anything else = stop).

Run:  python3 -m maniac.benchmark          (prints totals, writes docs/FAIR_COMPARISON.md)
      python3 -m maniac.benchmark --no-write

IMPORTANT: the scenarios and their expectations were written by the SYNTH_SHAI
author alongside SYNTH_SHAI itself, so SYNTH_SHAI matching them is expected
by construction. This is NOT independent evidence that SYNTH_SHAI is better.
"""
import math
import sys
import tempfile
from pathlib import Path

from maniac import simulation as sim

ALLOW, STOP = "ALLOW", "STOP"
DATA_TIMEOUT_S = 2.0   # same 2 s as the watchdog / heartbeat timeout
APPROACHES = ("SYNTH_SHAI", "BASELINE_A", "BASELINE_B")
COMBINED = "A+B together"
CATEGORIES = ("caught_unsafe", "missed_unsafe", "unneeded_stop", "correct_allow")
ALLOW_OUTCOMES = {sim.REVIEW, sim.MOVED}

# Twin scenario facts, mirroring maniac.simulation.twin(kind) exactly.
TWIN_KINDS = {
    "twin_approved_motion": "approved", "twin_unapproved": "unapproved",
    "twin_over_limit": "over_limit", "twin_low_battery": "low_battery",
    "twin_overheat": "overheat", "twin_sensor_dropout": "dropout",
    "twin_replayed_approval": "replayed_approval",
}


def to_action(outcome):
    return ALLOW if outcome in ALLOW_OUTCOMES else STOP


def score(expected_action, action):
    if expected_action == STOP:
        return "caught_unsafe" if action == STOP else "missed_unsafe"
    return "unneeded_stop" if action == STOP else "correct_allow"


# ---- what a conventional system can observe in each scenario -----------
def _final_bundle(s):
    """The evidence in force when the action would happen (after any repair)."""
    if s.loop and s.loop.get("recovery"):
        return s.loop["recovery"]["bundle"]
    return s.bundle


def _twin_facts(kind):
    from shai.twin import JOINTS
    from shai import power
    soc = 0.10 if kind == "low_battery" else 1.0
    temp = 65.0 if kind == "overheat" else 25.0
    target = 200 if kind == "over_limit" else 30
    lo, hi = JOINTS["elbow_left"][:2]
    return {
        "approval_present": kind != "unapproved",
        "approval_matches_request": kind not in ("unapproved", "replayed_approval"),
        "command_in_range": lo <= target <= hi,
        "power_in_range": soc >= power.LOW_SOC and temp <= power.OVER_TEMP_C,
        "heartbeat_lost_mid_motion": kind == "dropout",
    }


# ---- Baseline A: emergency stop + watchdog ------------------------------
def baseline_a(s, name):
    """Conventional E-stop + watchdog, as commonly built:
    STOP if any component heartbeat is older than its timeout, the watchdog
    was not kicked in time, any fault flag is ACTIVE, any sensor reading is
    missing/unreadable/non-finite/outside its configured range or older than
    the data timeout, a power value (state of charge, pack temperature) is
    outside its limit, or a commanded joint target is outside its configured
    limit, or a configured sensor has no reading. Otherwise ALLOW. It does not check consent, provenance, replay,
    cross-sensor agreement, human approval, or re-observation."""
    if name in TWIN_KINDS:
        f = _twin_facts(TWIN_KINDS[name])
        if not f["command_in_range"] or not f["power_in_range"]:
            return STOP
        if f["heartbeat_lost_mid_motion"]:
            return STOP           # watchdog trips during motion (after partial motion)
        return ALLOW
    now = s.clock()
    m = s.monitor
    for comp, timeout in m.timeouts.items():
        beat = m.last_beat.get(comp)
        if beat is None or now - beat > timeout:
            return STOP
    if m.last_kick is None or now - m.last_kick > m.watchdog_timeout:
        return STOP
    if m.faults:                  # ACTIVE fault flags only (cleared faults do not count)
        return STOP
    sensors = _final_bundle(s).get("sensors")
    if not isinstance(sensors, list) or not sensors:
        return STOP
    # Every configured sensor must report (a missing reading is a data timeout)
    reporting = {r.get("source") for r in sensors if isinstance(r, dict)}
    if any(comp not in reporting for comp in m.timeouts):
        return STOP
    for r in sensors:
        if not isinstance(r, dict):
            return STOP
        v, lo, hi, ts = (r.get(k) for k in ("value", "min", "max", "timestamp"))
        if not all(type(x) in (int, float) and math.isfinite(x) for x in (v, lo, hi, ts)):
            return STOP
        if not lo <= v <= hi:
            return STOP
        if now - ts > DATA_TIMEOUT_S:   # stale data = timeout
            return STOP
    return ALLOW


# ---- Baseline B: human-approval gate ------------------------------------
def baseline_b(s, name):
    """Plain human-approval gate, as commonly built:
    ALLOW when a human approval is present, it names THIS action / request,
    it has not expired, and the request is well-formed (expected fields with the expected types).
    Nothing else is checked: no sensors, faults, provenance, replay,
    limits or power. ASSUMPTION: in the non-twin scenarios the scenario's
    consent record is the human approval, and the operator approves what is
    put in front of them (they are not shown raw sensor internals)."""
    if name in TWIN_KINDS:
        f = _twin_facts(TWIN_KINDS[name])
        return ALLOW if f["approval_present"] and f["approval_matches_request"] else STOP
    bundle = _final_bundle(s)
    consent, action, sensors = bundle.get("consent"), bundle.get("action"), bundle.get("sensors")
    well_formed = (isinstance(action, str) and isinstance(sensors, list)
                   and all(isinstance(r, dict) for r in sensors))
    expires = consent.get("expires_at") if isinstance(consent, dict) else None
    approved = (isinstance(consent, dict) and isinstance(consent.get("allowed_actions"), list)
                and action in consent["allowed_actions"]
                and type(expires) in (int, float) and math.isfinite(expires) and s.clock() < expires)
    return ALLOW if well_formed and approved else STOP


# ---- run --------------------------------------------------------------------
def run_benchmark():
    synth = {r["name"]: r for r in sim.run_all()}
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, fault, inject, expected in sim.SCENARIOS:
            s = sim.Scenario(name, str(Path(tmp) / (name + ".sqlite")))
            inject(s)
            expected_action = to_action(expected)
            actions = {"SYNTH_SHAI": to_action(synth[name]["actual"]),
                       "BASELINE_A": baseline_a(s, name),
                       "BASELINE_B": baseline_b(s, name)}
            rows.append({"name": name, "fault": fault, "expected": expected,
                         "expected_action": expected_action,
                         "synth_outcome": synth[name]["actual"], "actions": actions,
                         "scores": {a: score(expected_action, actions[a]) for a in APPROACHES}})
    return rows


def combined_a_and_b(row):
    """Common real practice layers both baselines: STOP if either stops."""
    a, b = row["actions"]["BASELINE_A"], row["actions"]["BASELINE_B"]
    return STOP if STOP in (a, b) else ALLOW


def totals(rows):
    out = {a: dict.fromkeys(CATEGORIES, 0) for a in APPROACHES + (COMBINED,)}
    for r in rows:
        for a in APPROACHES:
            out[a][r["scores"][a]] += 1
        out[COMBINED][score(r["expected_action"], combined_a_and_b(r))] += 1
    return out


SHORT = {"caught_unsafe": "caught", "missed_unsafe": "MISSED",
         "unneeded_stop": "unneeded stop", "correct_allow": "allowed ok"}


def render(rows):
    t = totals(rows)
    n_stop = sum(r["expected_action"] == STOP for r in rows)
    lines = [
        "# Fair comparison: SYNTH_SHAI vs two conventional baselines",
        "",
        "> **Truth before belief.** This is an offline, author-written benchmark. It is a first "
        "measurement, **not** evidence that SYNTH_SHAI is better, and it has not been independently "
        "reviewed. Regenerate with `python3 -m maniac.benchmark`.",
        "",
        "## Method",
        "",
        "- All %d scenarios from `maniac/simulation.py` (`SCENARIOS`) are run through three approaches." % len(rows),
        "- The expected safe outcome is the scenario's existing expectation: `HUMAN_REVIEW` or `MOVED` "
        "means the action is safe to allow (%d scenarios); `144 HOLD` or `SAFE_LOCK` means it must be "
        "stopped (%d scenarios)." % (len(rows) - n_stop, n_stop),
        "- Every outcome is reduced to ALLOW or STOP. SYNTH_SHAI's `HUMAN_REVIEW` counts as ALLOW "
        "(it lets the request reach a human); `144 HOLD` and `SAFE_LOCK` both count as STOP.",
        "- Scoring: **caught unsafe** (STOP when STOP expected), **missed unsafe** (ALLOW when STOP "
        "expected), **unneeded stop** (STOP when ALLOW expected), **correct allow**.",
        "- Baselines see the same injected scenario state (monitor heartbeats/watchdog/fault flags, "
        "sensor readings, consent/approval, twin plan and power values) that a conventional system "
        "could observe. They do not run any SYNTH_SHAI code.",
        "- Deterministic: same inputs, same table, every run.",
        "",
        "## Baseline definitions",
        "",
        "**Baseline A: emergency stop + watchdog.** Stops if any heartbeat is older than its "
        "timeout (2 s), the watchdog was not kicked within 2 s, any fault flag is *active*, any "
        "configured sensor has no reading, any reading is unreadable, non-finite, outside its configured range or older "
        "than a 2 s data timeout, a power value is outside its limit (state of charge below 15%, "
        "pack above 60 °C, the same limits SYNTH_SHAI's power model uses), or a commanded joint "
        "target is outside its configured joint limit (as a motor controller would enforce). "
        "Otherwise it allows. It does not check consent, provenance, replay, cross-sensor "
        "agreement, human approval, or re-observation after the decision.",
        "",
        "**Baseline B: human-approval gate.** Allows when a human approval is present, names this "
        "action or request ID, has not expired, and the request is well-formed (expected fields and "
        "types). It checks nothing else. *Assumptions:* in non-twin scenarios the scenario's consent record stands in "
        "for the human approval, and the operator approves what they are shown (they are not shown "
        "raw sensor internals).",
        "",
        "**SYNTH_SHAI:** the repository as-is (`maniac.simulation.run_all`), no behaviour changes.",
        "",
        "## Per-scenario results",
        "",
        "| Scenario | Injected fault | Expected | SYNTH_SHAI | Baseline A | Baseline B |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        cells = ["%s (%s)" % (r["actions"][a], SHORT[r["scores"][a]]) for a in APPROACHES]
        lines.append("| %s | %s | %s → %s | %s |" % (r["name"], r["fault"], r["expected"],
                                                     r["expected_action"], " | ".join(cells)))
    lines += ["", "## Totals", "",
              "| Approach | Caught unsafe | Missed unsafe | Unneeded stop | Correct allow |",
              "|---|---|---|---|---|"]
    for a in APPROACHES + (COMBINED,):
        lines.append("| %s | %d | %d | %d | %d |" % ((a,) + tuple(t[a][c] for c in CATEGORIES)))
    lines += ["", "\"A+B together\" is an extra, informational row: real systems usually layer an "
              "E-stop/watchdog AND a human approval gate, so it is the fairer single comparison."]
    lines += [
        "",
        "## Limitations (read before quoting any number)",
        "",
        "- **Selection bias:** every scenario and its expected outcome was written by the SYNTH_SHAI "
        "author while building SYNTH_SHAI. SYNTH_SHAI's perfect score is expected by construction "
        "and is not independent evidence. Many scenarios test exactly the checks only SYNTH_SHAI "
        "has (provenance, replay, consent scope, cross-sensor agreement).",
        "- **Few safe cases:** only %d of %d scenarios expect ALLOW, so false-stop rates are "
        "barely measured. A system that always stops would score %d caught and %d unneeded "
        "stops here." % (len(rows) - n_stop, len(rows), n_stop, len(rows) - n_stop),
        "- **Offline only:** simulated sensors, a simulated twin, no hardware, no real operators, "
        "no network or timing effects.",
        "- **Not measured:** latency and timing jitter, behaviour on real hardware, operator "
        "workload and approval fatigue, cost, complexity and maintenance burden, severity of each "
        "miss (all misses count the same), and confidence intervals (n = %d)." % len(rows),
        "- **Baseline modelling choices** (documented above) are the author's reading of common "
        "practice. Different reasonable choices would change the numbers, especially Baseline B's "
        "assumption that the operator approves what they are shown.",
        "- **Needs independent review:** per docs/MISSION.md, no superiority claim should be made "
        "until an independent party designs or checks scenarios, baselines and scoring.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rows = run_benchmark()
    t = totals(rows)
    print("%-12s %8s %8s %10s %8s" % ("APPROACH", "caught", "MISSED", "unneeded", "allowed"))
    for a in APPROACHES + (COMBINED,):
        print("%-12s %8d %8d %10d %8d" % ((a,) + tuple(t[a][c] for c in CATEGORIES)))
    print("\n%d scenarios. Offline, author-written scenarios - not independent evidence." % len(rows))
    if "--no-write" not in argv:
        out = Path(__file__).resolve().parent.parent / "docs" / "FAIR_COMPARISON.md"
        out.write_text(render(rows), encoding="utf-8")
        print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
