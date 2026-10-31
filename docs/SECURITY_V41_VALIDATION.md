# SYNTH_SHAI V4.1 — Offline execution-boundary validation handoff

**Status: RESEARCH / 144 HOLD.** Updated 1 November 2026. This is an author-maintained testing plan, not independent security certification and not approval for live execution.

## Evidence already present (project-maintained)

- `offline_operator_admin_v2.py` implements Ed25519-signed revocation against pinned administrator keys and a local SQLite store. Tests in `test_offline_operator_admin_v2.py` exercise the local design. Key provisioning and real operator identity are **not independently authenticated**.
- `offline_preflight_v3.py` checks fixed prohibited actions, a trusted allowlist and a signed one-use approval. Positive results are `REVIEW_REQUIRED_NO_EXECUTION`, not permission to act.
- `offline_dispatch_v3.py` only produces a fixed synthetic review result. It has no real hardware, filesystem, command or network effect.
- `offline_worker_v3.py` moves the check into a one-shot spawned process and decodes bounded JSON bytes, not untrusted Python callables. It assumes its parent and launch configuration are trustworthy.
- `offline_sandbox_v4.py` applies Linux `RLIMIT_CPU`, `RLIMIT_AS`, `RLIMIT_FSIZE` and `RLIMIT_NOFILE` inside the child before receiving the request. The existing V4 tests inspect those limits. They **do not** verify filesystem, network, user-identity or capability isolation.

## Additional bounded V4.1 checks

Run on an isolated Linux development machine with test keys and a temporary database:

```bash
python3 -m unittest -v test_v41_offline_boundary
python3 -m unittest -v test_offline_sandbox_v4 test_offline_worker_v3 test_offline_preflight_v3 test_offline_dispatch_v3 test_offline_operator_admin_v2
```

`test_v41_offline_boundary.py` checks (1) failure to initialize OS limits returns HOLD without processing a request, (2) user messages cannot override startup trust keys, database path or clock, (3) duplicate JSON fields fail closed, (4) oversized input fails closed, and (5) denied inputs do not consume the subsequently submitted legitimate one-use approval. These are **negative application-path regressions** only. A passing CI result is NOT an independent OS sandbox assessment.

A hung or crashed child must be treated as **no authorization**, regardless of whether it returns a formatted HOLD response. The provided tests assert a bounded reply, but the parent service must itself enforce timeouts and terminate/reap workers; this is an outstanding controller requirement.

## External specialist's validation matrix (all open)

| Boundary | Acceptance question | Needed evidence |
| --- | --- | --- |
| Trusted operator identity | Who provisions, rotates and revokes administrator/operator keys, and what binds keys to humans? | Independent threat analysis, auditable trusted provisioning, key custody/rotation tests |
| Default deny | Can any unapproved, revoked, expired, replayed, malformed or crash-path request lead to *any* effect? | Independent negative-path matrix, multi-process race and restart evidence |
| Process separation | Does the worker have a distinct least-privilege identity, trusted parent channel and enforceable capability boundary? | OS process/identity inspection, IPC peer authentication and privilege model |
| Filesystem | Can the worker read/write host secrets, unapproved paths or inherited file descriptors? | Controlled filesystem access probes in disposable isolated environment; deny-by-default evidence |
| Network | Can the worker create sockets or reach external interfaces? | Controlled loopback/egress attempts within isolated test network; kernel enforcement evidence |
| Resource exhaustion | What happens to CPU, memory, disk, descriptors, child processes and parent liveness under pressure? | Independent stress tests, parent timeout/kill/reap observations, limits applied *before* untrusted code |
| Audit & recovery | Can a local adversary rewrite/replay an approval store, and are revocations persistent across restart? | Multi-process transactional tests and external trust-anchor analysis |

**Do not interpret absent evidence as a passed test.** The current prototype intentionally lacks several controls above. Existing V4 rlimits do not establish these guarantees.

## Review and authorization gates

1. Have an external specialist inspect the exact commit, trusted launch path, threat model, tests and environmental assumptions.
2. Record independent findings as **PASS, FAIL, UNVERIFIED** with reproducible artifacts, named assessor and target revision. Keep internal CI results labelled **project-maintained**.
3. Remediate findings through separately reviewed changes and rerun adversarial tests. No user-supplied arbitrary handlers or live adapters should be introduced as part of this work.
4. Require a distinct, explicit, scope-bound human authorization **after** independent review and completion of environment-specific safety obligations. Until then: **144 HOLD**.

The Character.AI conversational character and this GitHub security research are separate; one does not enforce guarantees for the other.
