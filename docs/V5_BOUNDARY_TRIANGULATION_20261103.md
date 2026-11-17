# V5 boundary triangulation: offline kernel probes (3 November 2026)

**Decision: 144 HOLD.** This is a bounded *test-only* probe package, not a V5 isolated launcher, a production security barrier, or third-party assurance. It changes no SYNTH_SHAI worker, approval, dispatch, external service, or permission. Baseline before this PR: `main` at `a0a2ebce7425eda4870278c853a79d39e7f884b3` (PR #75). Existing issue: [#73](https://github.com/trimblemitch796-cell/SYNTH_SHAI/issues/73).

## 555000 — Triangulate demonstrated versus missing controls

PR #75's project-maintained [negative control](../test_v5_isolation_negative_control.py) proves V4 rlimits alone still permit reading/writing disposable host files and creating an AF_INET socket. Source inspection of `offline_parent_v41.py` confirms direct-child lifecycle cleanup and no process-tree, OS filesystem/network, or authenticated IPC boundary. The present test-only probes evaluate separate Linux kernel mechanisms; they are NOT wired into the worker path.

| Boundary | Narrow probe added | What a positive probe shows | What remains UNVERIFIED |
| --- | --- | --- | --- |
| Filesystem | Landlock denies **fresh** read/write on a synthetic local fixture after the Python child starts; unsupported setup returns HOLD/skip | Kernel refusal for the tested file operations on that host | Sandboxed worker launch, inherited descriptors, other filesystem syscalls, mounts, host secrets, denial before Python startup |
| Network | seccomp BPF filter denies one new `socket(AF_INET, ...)` syscall in a disposable child; baseline socket creation checked first | Kernel-enforced EPERM for **new socket()** under that filter on that host | `connect()` using already-open descriptors, Unix sockets, egress, other syscall routes, before-startup policy and worker integration |
| Descendants | **Not implemented in this PR** | None | Per-request cgroup containment, escaped sessions, kill/reap of entire tree and no survivors |
| IPC | `SO_PEERCRED` returns kernel peer PID/UID/GID for a local Unix socketpair despite forged payload text | Kernel credential *reading* of this same-process fixture | Parent-to-child identity binding, safe credential/pid lifetime, trust anchors, authenticated service IPC, caller authorization |

## 333000 — Define the enforcement acceptance contract

The **trusted external launcher**, not an untrusted Python child, must create an OS-restricted execution envelope **before** interpreter startup, configure a minimal filesystem allowlist and default-deny network, own a cgroup/process-tree containment boundary, and authenticate the connected local peer against independently trusted expected process identity. All setup failure paths must return `144 HOLD` without launching a worker or consuming an approval. The current one-shot synthetic reviewer must remain the only permitted target. An on-host preflight test that merely detects support is insufficient for this contract.

No arbitrary target, live tool, robotic actuator, key material, account integration, or production executor is introduced by these probes.

## 888000 — Reproducible scope and pass criteria

Run on an isolated Linux x86-64 development host:

```sh
python3 -m unittest -v test_v5_kernel_boundary_probes
python3 -m unittest discover -v
```

The three probe tests report `V5_PROBE_FS`, `V5_PROBE_SOCKET` and `V5_PROBE_IPC`. A test is **skipped** if Landlock/seccomp cannot be installed and reports `144 HOLD`. A test passes its denial assertion only after an independently accessible *synthetic* fixture is refused by kernel policy. The Unix-socket test confirms credential reading only, NOT authenticated production IPC. These are project-maintained probes and are not independent security verification.

**Local probe execution:** Linux x86-64 container, kernel `6.18.57` (3 November 2026): filesystem Landlock `ENOSYS` (`144 HOLD`, **skipped**); seccomp new-socket denial **passed**; same-process Unix socketpair peer-credentials read **passed**. This environment's Landlock absence does not establish whether a different host supports it. No kernel isolation policy was installed in any SYNTH_SHAI production path.

**Next work (not completed):** add an externally controlled, fail-closed launch service, cgroup descendant enforcement, and test-only acceptance criteria for kernel-enforced FS and network restrictions *before process startup*. Run separate authenticated IPC negative tests using a real peer process under independently pinned credentials. Obtain independent review and explicit human authorization before any consequential use.
