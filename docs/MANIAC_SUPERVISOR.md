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
