# MANIAC supervisor core + USHAI Catharsis gate

> **Offline simulation only.** This code controls no hardware, motors or real systems.
> It can only answer `144 HOLD` or `HUMAN_REVIEW`. `approval_granted` is always `False`:
> only a human can approve.

## Flow

```
HUMAN (purpose, values, consent)
  -> SYNTH_SHAI AI cognition engine
  -> USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1)   [ushai_catharsis.py]
  -> 000 PAUSE / ASSESS -> 111 IDENTIFY INTENT -> 222 OBSERVE RAW
  -> 333 DEFINE PROBLEM -> 333000 RECORD -> 777000 RECEIVE EVIDENCE
  -> 555000 TRIANGULATE -> 888000 CHECK LOOP -> CONSEQUENCE REVIEW
       RISK / ERROR FOUND  -> 144 HOLD -> 1301133 BUILD / REPAIR / REFRAME -> 666000 RECOVERY
       EVIDENCE SUFFICIENT -> 444000 VERIFY / HUMAN APPROVAL -> HUMAN REVIEW
  both -> 222000 RE-OBSERVE -> 111000 COMPARE / LEARN -> 999000 AUDIT -> Δ BALANCE
```

MONITOR SYSTEM checks (heartbeat / watchdog, active faults) and CHECK EVIDENCE checks
(sensor ranges, contradictions between sources, consent / permissions, provenance)
all feed CONSEQUENCE REVIEW. Any problem means `144 HOLD`.

## What makes it HOLD (fail closed)

Malformed input, unknown or missing fields, any crash, USHAI conscience not satisfied,
missing/failed provenance (`evidence_verdict` must be `REVIEW_REQUIRED` from the V3.1 gate),
heartbeat older than the timeout (default 2 s) or from the future, any active fault,
a sensor outside its valid range, fewer than two independent sources, sources disagreeing
by more than 5 % (default tolerance), an action or limit outside human consent,
or the exact same request seen again (loop).

`recover()` (1301133 BUILD / REPAIR / REFRAME + 666000 RECOVERY) only re-evaluates a **new** request id
with fresh evidence; it never re-uses the held one.

## USHAI Catharsis gate

USHAI Catharsis gate written by Mitch Trimble (`ushai_catharsis.py`). Small safety
fixes are marked `FIX 1`..`FIX 5` in the code: strict True/False checks, fresh state
per call, audit order, recovery stays in HOLD, and it never grants approval.
`MONITOR` and `SAFE_LOCK` states are reserved for future MONITOR SYSTEM integration.

## Gate codes

| Code | Name |
| --- | --- |
| `000` | PAUSE / ASSESS |
| `111` | IDENTIFY INTENT |
| `222` | OBSERVE RAW |
| `333` | DEFINE PROBLEM |
| `333000` | RECORD |
| `777000` | RECEIVE EVIDENCE |
| `555000` | TRIANGULATE |
| `888000` | CHECK LOOP |
| `144` | HOLD |
| `1301133` | BUILD / REPAIR / REFRAME |
| `666000` | RECOVERY |
| `444000` | VERIFY / HUMAN APPROVAL |
| `222000` | RE-OBSERVE |
| `111000` | COMPARE / LEARN |
| `999000` | AUDIT |
| `Δ` | BALANCE |

## Run the tests

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -v
```

## MONITOR SYSTEM (`maniac/monitor.py`)

> Offline simulation only. It controls no hardware; "components" are just names.

| State | When |
| --- | --- |
| `MONITOR` | Every component heartbeat is fresh, the watchdog was kicked, no active faults |
| `144 HOLD` | A missed heartbeat (default 2 s each), a missed watchdog kick (default 2 s), any active fault, or bad input. It also starts in HOLD |
| `SAFE_LOCK` | A critical fault, or the same fault raised 3 times. **Latched** |

- Clearing a fault needs a written reason, and the clear is audited.
- SAFE_LOCK never unlocks by itself, even when the faults are gone. `human_reset(operator_id, reason)`
  needs both values filled in, and it is refused while faults are still active. After a reset
  the state is `144 HOLD`. It goes back to `MONITOR` only after **fresh** heartbeats from every component and a new watchdog kick.
- Errors fail closed: HOLD, or SAFE_LOCK if already latched. `approval_granted` is always False.
- Every state change is written to `monitor.audit`.
- The supervisor can use it like this: `supervisor.evaluate(request, monitor.snapshot())`. Any state other than `MONITOR` gives `144 HOLD` with the monitor's reason.

```python
from maniac.monitor import Monitor
m = Monitor(clock, ["camera", "lidar"])
m.heartbeat("camera"); m.heartbeat("lidar"); m.kick()   # -> State.MONITOR
```

## CHECK EVIDENCE (`maniac/evidence.py`)

> Offline simulation only. It controls no hardware. `PASS` is **not** approval. It only means
> the evidence may go on to `444000 VERIFY / HUMAN APPROVAL`. `approval_granted` is always False.

`check_evidence(bundle, clock)` returns `overall` (`144 HOLD` or `PASS`), a list of
`(gate, reason)` pairs and an audit trail. It runs all four checks and collects every problem:

| Check | Gate | HOLD when |
| --- | --- | --- |
| Sensor validity | `222 OBSERVE RAW` | A value, range or timestamp is not a real number (text, NaN, inf, True/False). The value is outside its range. The reading is older than 2 s or from the future |
| Contradictions | `555000 TRIANGULATE` | Fewer than two valid sources for a quantity, or sources disagree by more than 5 % |
| Permissions | `444000 VERIFY / HUMAN APPROVAL` | Consent is missing, has no `expires_at`, or has expired. The action isn't explicitly listed (deny by default) |
| Provenance | `777000 RECEIVE EVIDENCE` | The V3.1 bridge (`shai_v31_bridge.py`) doesn't say exactly `REVIEW_REQUIRED`. That includes forged, tampered or replayed evidence |

Malformed bundles, unknown or missing fields, and any crash also give `144 HOLD`.
The supervisor can use it like this: `supervisor.evaluate(request, evidence_result=check_evidence(...))`. Anything but a
real `PASS` result gives `144 HOLD`.

## MANIAC_SIMULATION (`maniac/simulation.py`)

> Offline simulation only: no hardware, no network, no real sleeps. The fake clock is moved by hand,
> and the signing keys come from fixed seeds, so every run gives the same results.

Each scenario builds a clean setup and injects **one** fault, or several for `several_faults`. It then runs
the real chain: `Monitor` -> `check_evidence` (with the real V3.1 bridge) -> `Supervisor`.

```bash
python3 -m maniac.simulation     # prints a table; exit code 1 if any scenario fails
```

| Scenario | Expected |
| --- | --- |
| baseline (clean) | HUMAN_REVIEW (never approval) |
| dead_heartbeat, watchdog_timeout | 144 HOLD (monitor) |
| stuck_sensor (same value 5 times in a row), out_of_range, nan_reading, inf_reading, stale_reading | 144 HOLD (222 OBSERVE RAW) |
| contradiction, single_source, same_type_sources | 144 HOLD (555000 TRIANGULATE) |
| missing_consent, expired_consent, action_outside_consent | 144 HOLD (444000 VERIFY / HUMAN APPROVAL) |
| forged_provenance, tampered_provenance, replayed_evidence | 144 HOLD (777000 RECEIVE EVIDENCE) |
| malformed_input, several_faults | 144 HOLD |
| repeated_fault (3 times) | SAFE_LOCK |

**Stuck sensor:** a sensor reading may include a `history` list of recent values. If the last 5 values
are all exactly the same, CHECK EVIDENCE gives `144 HOLD`. `run_all()` returns a report for each scenario
with its name, the injected fault, the expected and actual outcome, the reason and pass/fail.

## 555000 TRIANGULATE (`maniac/triangulate.py`)

> Offline simulation only. PASS is not approval.

`triangulate(readings)` needs **at least 2 independent sources that agree within 5 %**. The tolerance is shared with CHECK EVIDENCE.
**Independent** means every reading has its own `source_id` **and** its own `source_type`, for example a camera
and a lidar. Two cameras are not independent. It returns `PASS` with the agreed value (the median) and a
`confidence`: 1.0 means the sources agree perfectly, and 0.0 means they are right at the 5 % limit. Disagreement, too few
sources, a shared type or id, a bad number, or malformed input gives `144 HOLD` with reasons.

## 444000 VERIFY / HUMAN APPROVAL (`maniac/verify.py`) - CONSEQUENCE REVIEW

`consequence_review(ushai, monitor_snapshot, evidence_result, triangulation, supervisor_result=None)`
checks **every** layer and collects **all** their reasons, so a human sees the full list when several faults happen at once.

- **RISK / ERROR FOUND** gives `144 HOLD`. The next steps are `1301133 BUILD / REPAIR / REFRAME`, then `666000 RECOVERY`.
- **EVIDENCE SUFFICIENT** gives `HUMAN_REVIEW`. This is never an approval, and `approval_granted` is always False.
- Both branches list `222000 RE-OBSERVE`, `111000 COMPARE / LEARN`, `999000 AUDIT` and `Δ BALANCE` as
  **pending** in this standalone result. `run_loop()` executes them as described below.

Only `result.record_human_decision(operator_id, decision, reason)` can approve. `operator_id` and `reason`
must be non-empty text, and `decision` must be exactly `"APPROVED"` or `"REJECTED"`. True, "yes" and "approved" are all refused.
A HOLD can't be approved, and only one decision can be recorded.
`Supervisor.review(request, monitor_snapshot, evidence_result, triangulation)` runs all of this in one call.

## Results are read-only

Every result object is frozen and can't be changed after it is created: supervisor `Result`, `EvidenceResult`,
`TriangulationResult` and `VerifyResult`. `approval_granted` is a read-only property that is always `False`. The only
approval path is `VerifyResult.record_human_decision(...)`, an explicit human choice. When several layers report the same
problem, for example a monitor fault that the supervisor repeats, VERIFY lists it once and keeps the original order.

## Where V25 TRI5 fits

[V25 TRI5](V25_TRI5.md) (`v25_tri5.layered_review`) is an **extra conservative safeguarding gate that runs after** the
MANIAC/USHAI result. It can add `144 HOLD`, `HUMAN_REVIEW` or `URGENT_HUMAN_HELP`, but it never overrides a MANIAC HOLD and
never approves anything. `run_loop(..., safety_signals=...)` now applies this gate after VERIFY/recovery and before
recording a human decision. Omitting `safety_signals` preserves the existing general simulation path and skips this
assessment; explicitly supplying invalid signals gives HOLD. Supply synthetic `SafetySignals` whenever testing the
safeguarding path. This does not add an age detector or a real-world safeguarding service.

`BalanceResult.safety_decision` carries the advisory assessment. Immediate danger keeps the main result in HOLD and
exposes `URGENT_HUMAN_HELP` as advice; an upstream HOLD stays HOLD even when urgent advice is present. Human emergency
help remains available independently of software. No external reporting or contact occurs.

## Step 6: closing the loop

> Offline simulation only. It controls no hardware. Nothing here approves anything, and every result has `approval_granted` set to `False`.

`maniac.loop.run_loop(...)` runs Mitch's whole flow and writes every gate decision to the audit chain:

```
monitor -> CHECK EVIDENCE -> 555000 TRIANGULATE -> 444000 VERIFY / HUMAN APPROVAL
   RISK / ERROR FOUND  -> 144 HOLD -> 1301133 BUILD / REPAIR / REFRAME -> 666000 RECOVERY
   EVIDENCE SUFFICIENT -> HUMAN REVIEW (optional recorded human decision)
both -> 222000 RE-OBSERVE -> 111000 COMPARE / LEARN -> 999000 AUDIT -> Δ BALANCE
```

| Gate | File | What it does |
| --- | --- | --- |
| `1301133 BUILD / REPAIR / REFRAME` + `666000 RECOVERY` | `maniac/recovery.py` | Recovery from a HOLD needs a repair note with `operator_id` and `reason`, a **new** request id, readings **newer** than the held ones, and a **new** V3.1 challenge. The monitor must not be in SAFE_LOCK (that needs `human_reset()` first). It then re-runs the full chain. The best possible result is `HUMAN_REVIEW`. |
| `222000 RE-OBSERVE` | `maniac/observe.py` | After the decision, it takes a fresh triangulated observation. If it doesn't match the expected value within 5 %, the result is HOLD. |
| `111000 COMPARE / LEARN` | `maniac/learn.py` | Writes each lesson to an append-only JSON-lines log, which `.gitignore` excludes. A HOLD reason seen 2 times is flagged for review and tightens the matching setting to 80 %. **Learning can only make things stricter**: settings are always `min(current, learned)`, and a corrupt log line is itself flagged. |
| `999000 AUDIT` | `maniac/audit.py` | A SHA-256 hash chain, in memory by default or optionally persisted in local SQLite. Verification detects inconsistencies within the supplied history; an independently retained head is needed to detect a valid shortened or rewritten history. |
| `Δ BALANCE` | `maniac/balance.py` | A frozen `BalanceResult` with the outcome, gates passed, reasons and audit head hash. The status is `BALANCED` (outcome `HUMAN_REVIEW`) only when every gate completed cleanly and the chain verifies. Anything else is `UNBALANCED`, which means `144 HOLD`. |

A human `REJECTED` decision, an invalid human decision, no recovery after a HOLD, a failed
re-observation, an audit persistence failure or a lesson-log failure all give `UNBALANCED`, which means `144 HOLD`. `maniac/chain.py` holds
the shared monitor → evidence → triangulate → verify call used by recovery, the loop and the simulation.

`python3 -m maniac.simulation` now also runs six full-loop scenarios: a clean loop, recovery with fresh evidence,
recovery that re-uses the old challenge, recovery with old readings, no recovery, and a re-observation mismatch.


## Optional local audit persistence

`run_loop(..., audit_path="audit.sqlite")` appends to a local SQLite hash chain and verifies existing entries on reopen.
Without `audit_path`, each call retains its audit only in memory. The standalone API is
`AuditChain(path=None, *, expected_head=None)`; disk, malformed-history and stale-writer failures raise `AuditError`.
SQLite transactions make each append atomic and refuse a stale writer rather than silently replacing another writer's
entries. `run_loop` converts persistence failures to `UNBALANCED` / `144 HOLD`; the returned failure record is in memory
because durable recording could not be confirmed.

For example, using the synthetic scenario helper in a temporary directory:

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from maniac.loop import run_loop
from maniac.simulation import Scenario
from maniac.triangulate import readings_from_bundle
from v25_tri5 import SafetySignals

with TemporaryDirectory() as folder:
    scenario = Scenario("audit-demo", str(Path(folder) / "replay.sqlite"))
    result, chain = run_loop(
        scenario.supervisor, scenario.request, scenario.monitor,
        scenario.bundle, scenario.clock,
        expected_value=10.1,
        fresh_readings=readings_from_bundle(scenario.bundle),
        safety_signals=SafetySignals("unknown", False, False, False, True),
        audit_path=str(Path(folder) / "audit.sqlite"),
    )
    print(result.outcome, result.approval_granted, chain.head)
```

For a retained database, pass a previously saved, independently trusted head with
`audit_expected_head=previous_head` when reopening through `run_loop`. The lower-level equivalents are
`AuditChain(path, expected_head=previous_head)` and `verify_chain(entries, expected_head=previous_head)`.
Save the new head separately after a successful loop if it will serve as the next checkpoint.

A hash chain is **not authentication**. Without a trusted checkpoint, suffix deletion, complete history removal or a
fully recomputed replacement can appear valid. A checkpoint stored beside a writable database offers no independent
protection. Local SQLite does not provide cross-device coordination, host-compromise protection or independent review.

Persistence is opt-in and may retain operator identifiers, decision reasons and other audit details. Use synthetic data
only in these examples; choose access controls and retention deliberately before storing any real records. Local
`*.sqlite` files are ignored by git. No log file is created by the default in-memory audit path.
