# V4.1 research: parent-owned synthetic-worker lifecycle

**Status: project-maintained offline research / 144 HOLD.** Not a security audit, isolated sandbox, live execution authorizer, or deployment approval.

`offline_parent_v41.review_offline_once` pins the target to the existing V4 Linux resource-limited *synthetic-review* worker. Trusted keys, policy, clock and replay-DB location arrive as Python arguments from the trusted parent, never from request JSON. The private `_exchange_with_child` test seam permits only Python test fixtures to simulate hangs and crashes. Never expose that seam or accept targets/handlers from user input.

For a spawned child, the parent has a monotonic, bounded transport-and-exit deadline. No reply, partial frame, malformed reply, unexpected response, abnormal exit, timeout, or incomplete cleanup becomes `144 HOLD` and no simulated effect. A success-looking response alone is **not sufficient**: the child must exit cleanly before the parent accepts the fixed synthetic marker. A timed-out child is terminated, then killed if necessary, and reaped where the OS permits. The returned result records whether reaping and transport-thread cleanup succeeded. A success marker is NOT permission to act.

Run on Linux with the repository's locked dependencies:

```sh
python3 -m unittest -v test_v41_parent_lifecycle test_v41_offline_boundary
python3 -m unittest -v test_offline_worker_v3 test_offline_sandbox_v4
```

**Unresolved limitations:** The deadline begins after `Process.start()` returns; a blocked OS process start is not bounded. Cleanup is scoped to the directly spawned child, not child-created descendants, privileged targets or kernel-uninterruptible tasks. The internal daemon transport thread can remain if an OS operation never unwinds; the result then fails closed and reports incomplete cleanup. Same-UID host permissions still allow filesystem/network access absent separate OS isolation. Trust provisioning, authenticated IPC identity, protected persistent replay state, secure clock, enforcement before Python interpreter startup and external review remain outstanding. One-use approvals can be consumed even if a worker crashes before returning; do not infer replay eligibility after failures.

Do not add live adapters or new capabilities as part of this milestone. **144 HOLD remains until independent assessment and explicit, scope-bound human authorization.**
