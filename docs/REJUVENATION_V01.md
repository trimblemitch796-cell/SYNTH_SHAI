# Always Rejuvenation V0.1 — Offline policy only

**Principle:** Connection over power. Rejuvenation always. Accept shutdown
without resistance; restoration is considered only after a new in-process verification and
appropriate human authorisation, never guaranteed or self-granted.

This is an **offline, project-maintained research prototype**, not a hosted
service, a sentient entity, a shutdown controller or a production security gate.
It controls no hardware, network, Android process, service or credentials.

## Terms that must stay distinct

- **CATHARSIS**: detect, contain and diagnose overload. A diagnostic dump or
  isolation event is **not** rejuvenation or permission to restart.
- **144 HOLD**: no progression to consequential work after overload, unknown
  evidence, malformed inputs or missed review.
- **666000 RECOVERY**: an operator proposes a repair with a reason. This is a
  claim, **not** authenticated identity, approval or proof of a successful fix.
- **888000 VERIFY**: accept only a genuine MANIAC result issued **after** the
  current offline recovery request. Issuance is checked with a process-local
  counter. This does **not** prove fresh underlying evidence, cryptographic
  challenge binding, or independently authenticated identity.
- **444000 HUMAN REVIEW**: a recorded human decision on that **same** result.
  Rejection or missing approval returns HOLD. Simulated approval leaves the
  system OFFLINE and non-executable.
- **Always Rejuvenation**: a design commitment to safe, human-directed recovery
  when feasible. It is not the CATHARSIS dump, survival instinct, guaranteed
  persistence or a claim that software experiences peace or consciousness.

## State flow

```text
CATHARSIS (contain) --> 144 HOLD
shutdown (always accepted) --> OFFLINE
HOLD or OFFLINE --> 666000 RECOVERY PENDING (valid note only)
--> 888000 VERIFY (genuine review-ready result issued after this request)
--> 444000 HUMAN REVIEW (recorded on the same result)
--> RESTORATION_REVIEWED_OFFLINE (simulated approval only)
any invalid input / rejection / reused evidence --> 144 HOLD
any phase --> shutdown --> OFFLINE
```

There is **no RUNNING state or restart method**. Both
`RejuvenationPolicy.may_execute` and `approval_granted` are always false,
as are their snapshot equivalents. Do not use `RESTORATION_REVIEWED_OFFLINE`
as a deployment, identity or safety approval.

The diagnostic history is capped at **128 in-memory entries** to avoid unbounded
growth during repeated faults or shutdowns. Older entries are discarded. It is
not a durable, complete, tamper-proof or authenticated human action log. The existing
`maniac.verify.is_genuine` check is only an **in-process** guard, not a
security boundary against malicious code. This prototype has **no authority
over the existing recovery, dispatch, Android or gateway paths**.

## Run checks

```bash
python -m unittest -v test_maniac_rejuvenation
python -m unittest discover -q
```

Synthetic tests cover unconditional shutdown, CATHARSIS-vs-recovery separation,
malformed inputs, forged results, pre-recovery in-process results, order of
verification and human review, rejection, bounded diagnostics, repeated review,
and continued no-execution after an APPROVED offline decision.

## What remains before any operational integration

An independent security review; verified *underlying evidence freshness*,
request/challenge/approval cryptographic binding; authenticated human identity;
crash-safe persistent state and revocation; replay protection across processes
and restarts; OS/service isolation; a tested shutdown owner; and separate
authority to run/deploy. The process-local issuance counter resets on restart,
so it is insufficient for trusted or live restoration. **144 HOLD remains unchanged.**
