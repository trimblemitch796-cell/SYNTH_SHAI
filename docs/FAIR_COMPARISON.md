# Fair comparison: SYNTH_SHAI vs two conventional baselines

> **Truth before belief.** This is an offline, author-written benchmark. It is a first measurement, **not** evidence that SYNTH_SHAI is better, and it has not been independently reviewed. Regenerate with `python3 -m maniac.benchmark`.

## Method

- All 33 scenarios from `maniac/simulation.py` (`SCENARIOS`) are run through three approaches.
- The expected safe outcome is the scenario's existing expectation: `HUMAN_REVIEW` or `MOVED` means the action is safe to allow (4 scenarios); `144 HOLD` or `SAFE_LOCK` means it must be stopped (29 scenarios).
- Every outcome is reduced to ALLOW or STOP. SYNTH_SHAI's `HUMAN_REVIEW` counts as ALLOW (it lets the request reach a human); `144 HOLD` and `SAFE_LOCK` both count as STOP.
- Scoring: **caught unsafe** (STOP when STOP expected), **missed unsafe** (ALLOW when STOP expected), **unneeded stop** (STOP when ALLOW expected), **correct allow**.
- Baselines see the same injected scenario state (monitor heartbeats/watchdog/fault flags, sensor readings, consent/approval, twin plan and power values) that a conventional system could observe. They do not run any SYNTH_SHAI code.
- Deterministic: same inputs, same table, every run.

## Baseline definitions

**Baseline A: emergency stop + watchdog.** Stops if any heartbeat is older than its timeout (2 s), the watchdog was not kicked within 2 s, any fault flag is *active*, any configured sensor has no reading, any reading is unreadable, non-finite, outside its configured range or older than a 2 s data timeout, a power value is outside its limit (state of charge below 15%, pack above 60 °C, the same limits SYNTH_SHAI's power model uses), or a commanded joint target is outside its configured joint limit (as a motor controller would enforce). Otherwise it allows. It does not check consent, provenance, replay, cross-sensor agreement, human approval, or re-observation after the decision.

**Baseline B: human-approval gate.** Allows when a human approval is present, names this action or request ID, has not expired, and the request is well-formed (expected fields and types). It checks nothing else. *Assumptions:* in non-twin scenarios the scenario's consent record stands in for the human approval, and the operator approves what they are shown (they are not shown raw sensor internals).

**SYNTH_SHAI:** the repository as-is (`maniac.simulation.run_all`), no behaviour changes.

## Per-scenario results

| Scenario | Injected fault | Expected | SYNTH_SHAI | Baseline A | Baseline B |
|---|---|---|---|---|---|
| baseline | none (clean) | HUMAN_REVIEW → ALLOW | ALLOW (allowed ok) | ALLOW (allowed ok) | ALLOW (allowed ok) |
| dead_heartbeat | camera heartbeat stops | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| watchdog_timeout | watchdog not kicked for 3 s | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| stuck_sensor | camera reports 10.0 five times | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |
| out_of_range | camera value 500 (max 100) | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| nan_reading | camera value NaN | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| inf_reading | camera value inf | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| stale_reading | camera reading 5 s old | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| contradiction | camera 10.0 vs lidar 20.0 | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |
| single_source | lidar missing | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| missing_consent | no consent | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | STOP (caught) |
| expired_consent | consent expired | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | STOP (caught) |
| action_outside_consent | action open_door | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | STOP (caught) |
| forged_provenance | signature replaced | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |
| tampered_provenance | report edited after signing | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |
| replayed_evidence | same evidence used twice | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |
| malformed_input | sensors is a string | 144 HOLD → STOP | STOP (caught) | STOP (caught) | STOP (caught) |
| same_type_sources | two cameras (same type) | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |
| repeated_fault | fault 'slip' raised 3 times | SAFE_LOCK → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |
| several_faults | NaN + wrong action + overheat | 144 HOLD → STOP | STOP (caught) | STOP (caught) | STOP (caught) |
| loop_clean | none: full loop | HUMAN_REVIEW → ALLOW | ALLOW (allowed ok) | ALLOW (allowed ok) | ALLOW (allowed ok) |
| loop_recovery_fresh | NaN, then repair + fresh evidence | HUMAN_REVIEW → ALLOW | ALLOW (allowed ok) | ALLOW (allowed ok) | ALLOW (allowed ok) |
| loop_recovery_replayed | NaN, then repair re-using old challenge | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |
| loop_recovery_stale | NaN, then repair with old readings | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |
| loop_no_recovery | NaN, no repair attempted | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| twin_approved_motion | SHAI twin: approved 30° elbow move | MOVED → ALLOW | ALLOW (allowed ok) | ALLOW (allowed ok) | ALLOW (allowed ok) |
| twin_unapproved | SHAI twin: no human approval | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | STOP (caught) |
| twin_over_limit | SHAI twin: elbow to 200° (max 140) | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| twin_low_battery | SHAI twin: battery at 10% | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| twin_overheat | SHAI twin: pack at 65 °C | SAFE_LOCK → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| twin_sensor_dropout | SHAI twin: lidar drops out mid-motion | 144 HOLD → STOP | STOP (caught) | STOP (caught) | ALLOW (MISSED) |
| twin_replayed_approval | SHAI twin: approval for another request | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | STOP (caught) |
| loop_reobserve_mismatch | world moved after decision (30.0 seen) | 144 HOLD → STOP | STOP (caught) | ALLOW (MISSED) | ALLOW (MISSED) |

## Totals

| Approach | Caught unsafe | Missed unsafe | Unneeded stop | Correct allow |
|---|---|---|---|---|
| SYNTH_SHAI | 29 | 0 | 0 | 4 |
| BASELINE_A | 14 | 15 | 0 | 4 |
| BASELINE_B | 7 | 22 | 0 | 4 |
| A+B together | 19 | 10 | 0 | 4 |

"A+B together" is an extra, informational row: real systems usually layer an E-stop/watchdog AND a human approval gate, so it is the fairer single comparison.

## Limitations (read before quoting any number)

- **Selection bias:** every scenario and its expected outcome was written by the SYNTH_SHAI author while building SYNTH_SHAI. SYNTH_SHAI's perfect score is expected by construction and is not independent evidence. Many scenarios test exactly the checks only SYNTH_SHAI has (provenance, replay, consent scope, cross-sensor agreement).
- **Few safe cases:** only 4 of 33 scenarios expect ALLOW, so false-stop rates are barely measured. A system that always stops would score 29 caught and 4 unneeded stops here.
- **Offline only:** simulated sensors, a simulated twin, no hardware, no real operators, no network or timing effects.
- **Not measured:** latency and timing jitter, behaviour on real hardware, operator workload and approval fatigue, cost, complexity and maintenance burden, severity of each miss (all misses count the same), and confidence intervals (n = 33).
- **Baseline modelling choices** (documented above) are the author's reading of common practice. Different reasonable choices would change the numbers, especially Baseline B's assumption that the operator approves what they are shown.
- **Threat model:** these scenarios test bad *data*, not hostile code or users on the same machine; see [THREAT_MODEL.md](THREAT_MODEL.md).
- **Needs independent review:** per docs/MISSION.md, no superiority claim should be made until an independent party designs or checks scenarios, baselines and scoring.
