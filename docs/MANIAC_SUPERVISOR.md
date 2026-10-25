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
       RISK / ERROR FOUND  -> 144 HOLD -> 1301133 REPAIR -> 666000 RECOVERY
       EVIDENCE SUFFICIENT -> 444000 VERIFY -> HUMAN REVIEW
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

`recover()` (1301133 REPAIR + 666000 RECOVERY) only re-evaluates a **new** request id
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
