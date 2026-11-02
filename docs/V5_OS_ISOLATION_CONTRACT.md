# V5 trusted OS isolation contract — design and acceptance gates

**Status: OPEN ENGINEERING CONTRACT / 144 HOLD — no verified OS isolation.** Baseline on 2 November 2026: `93708f8ae46a9d2f772adce4ead7215ca7270af2`. Follow-up: [issue #73](https://github.com/trimblemitch796-cell/SYNTH_SHAI/issues/73).

## Current enforced *offline* boundary

`offline_parent_v41.review_offline_once` pins `limited_worker_once` to a fixed synthetic review. It validates a one-shot byte reply, accepts only the synthetic marker after clean direct-child exit, and attempts direct-child terminate / kill / reap on fault. Nine project-maintained fault-injection tests passed on Python 3.11 and 3.13 after PR #72 merged. This is **not** a sandbox or trusted execution authority. V4 Linux rlimits are applied inside Python after interpreter startup.

## Proposed trusted architecture (not implemented)

```text
Trusted operator + scoped approval + independently authenticated identity
    |
    v
Trusted external launcher / isolated service (separate privilege boundary)
    |-- setup restricted service UID / namespace / mounts / seccomp or sandbox
    |-- deny filesystem access except explicit temporary allowlist
    |-- deny all network/loopback egress unless explicitly required and verified
    |-- open only owned IPC channel; verify peer credentials and channel integrity
    |-- assign per-request cgroup or equivalent OS process-tree containment
    |-- enforce launch+runtime monotonic wall-clock limit OUTSIDE worker
    |-- kill and reap entire contained process tree on error
    v
Fixed V4 synthetic reviewer (no live execution capabilities)
    |
    v
Exact synthetic result only -> human review, NEVER permission to execute
```

**Important:** A Python `multiprocessing` worker cannot authenticate itself as a trusted OS boundary. Python `os.setuid()`, rlimits, `close_fds`, or a process group by themselves do **not** prove isolation; a descendant can escape a process group, and `Process.start()` may block before the existing deadline begins. Do not elevate privilege to run acceptance tests. Never attach real capabilities to this design while any acceptance gate is open.

## Verification matrix (all currently UNVERIFIED)

| Boundary | Smallest controlled offline acceptance test | Required evidence |
| --- | --- | --- |
| Trusted launch | Stall before worker PID handoff; parent-owned external supervisor applies total deadline and returns HOLD | Timed observation, no unbounded `Process.start`, exact exit and cleanup record |
| Descendants | Synthetic worker spawns a direct descendant and a descendant that attempts `setsid()`; provoke timeout | All descendants in a disposable OS containment scope terminated/reaped; no surviving PIDs/capabilities |
| Filesystem | Disposable sandbox with fake secret and writable decoy outside allowlist | OS-denied read, write, rename and open-FD inheritance; no host secret access |
| Network | Under an isolated test network, try loopback and socket egress without real external targets | Kernel-enforced denial; packet/FD evidence, not just Python exceptions |
| Identity | Launch with a dedicated unprivileged identity and no privileged inherited FDs | Effective credentials, capabilities, mounts and FDs verified from trusted parent |
| IPC | Attempt connect as a different local UID/process and replay/tamper bytes | Verified `SO_PEERCRED` / equivalent peer binding, message integrity and nonce scope |
| Setup failure | Fail namespace/cgroup/seccomp/mount/identity configuration **before** starting worker | No child runs, no approval consumed, controller returns HOLD and auditable failure |
| Independence | Qualified external assessor reproduces from pinned SHA and reports gaps | Signed or attributable PASS/FAIL/UNVERIFIED matrix with OS/kernel details |

## Implementation discipline

1. External launcher owns all capability handles; no untrusted-supplied callback, command, path, config, key or execution handler.
2. Add the smallest offline OS boundary probe on a **separate PR** using fake paths and local-only IPC. Never run probes against live accounts, systems, or sensitive files.
3. Test environment-specific support first (Linux namespace/cgroup/seccomp and permissions). Unsupported configurations **fail closed**, not skip into “secure.”
4. Record which properties are structurally prevented by kernel policy versus merely inferred from passing application tests.
5. Require independent specialist assessment and explicit `444000` human authorization for each contemplated real-world integration.

**Review status: 144 HOLD.** This file is a testable design contract, **not** evidence that the listed OS restrictions have been implemented.
