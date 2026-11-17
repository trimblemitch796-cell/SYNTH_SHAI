# V5 fixed-target systemd isolation experiment (3 November 2026)

**Status: review candidate / no verified integrated OS isolation / 144 HOLD.**
Starting baseline: `main` at `a0a2ebce7425eda4870278c853a79d39e7f884b3` (PR #75). Related: [V5 acceptance issue #73](https://github.com/trimblemitch796-cell/SYNTH_SHAI/issues/73) and the independent [kernel-probe PR #76](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/76).

## What this adds

`v5_systemd_isolation_probe.py` asks a **user systemd manager** to start exactly one fixed, disposable Python fixture. It uses a generated unique service name, a synthetic file under a temporary directory, and an unconnected internet-family socket. `systemd-run --user --wait --pipe --collect --service-type=exec` carries only a static Python script and two parent-generated fixture arguments. No shell or user-defined program or target is accepted. No SYNTH_SHAI worker, signed approval, account, robot, or remote network destination is used.

The transient **service** is requested with pre-start restrictions:

- `ProtectSystem=strict`, `ProtectHome=yes`, and `InaccessiblePaths=<synthetic temporary directory>` for filesystem isolation of the controlled fixture.
- `PrivateNetwork=yes` and `RestrictAddressFamilies=AF_UNIX` to prevent new AF_INET sockets; no network connection is made.
- `NoNewPrivileges=yes`, `CapabilityBoundingSet=`, `AmbientCapabilities=`, `SystemCallFilter=~@mount`.
- `RuntimeMaxSec=5s`, `TimeoutStartSec=5s`, `KillMode=control-group`, `TasksMax=16`, `MemoryMax=256M` as attempted group lifecycle limits.

**These are requested unit properties, not evidence that the host's systemd actually applied them.** A passing mock test cannot establish kernel enforcement. The code accepts a synthetic observation only if the manager exits successfully, an exact nonce-matched JSON object is returned, and both file-denial signals and the new-socket-denial signal are true. The synthetic observation token is **not approval or authorization**.

## How to reproduce

```sh
python3 -m unittest -v test_v5_systemd_isolation_probe
# Optional manual disposable experiment on a Linux host with a working user
# systemd manager; it never launches an actual SYNTH_SHAI worker:
python3 v5_systemd_isolation_probe.py
```

If the user systemd manager or namespace support is missing, or startup fails, the experiment returns `144 HOLD`. This is normal and is **not a denial PASS**.

**Local observation, 3 Nov 2026:** Linux x86-64, systemd 257 installed but no accessible system/user manager. Eight local tests passed, covering fixed command construction, failure/timeout to HOLD, invalid output, duplicate fields, wrong nonce and forged success. The real subprocess attempt returned `{"decision":"144 HOLD","reason":"systemd_service_failed"}`. **Actual managed-launch isolation was not demonstrated locally.**

## Explicit gaps still open

1. A true trusted, external systemd service that starts the **actual fixed V4 synthetic reviewer**, with isolation applied before its Python interpreter starts. This PR is a *probe-only* proof-of-concept; no executor integration.
2. Filesystem allowlisting beyond one inaccessible synthetic directory; inherited open descriptors, system mounts, arbitrary paths and process privilege boundaries remain outside this experiment.
3. Network isolation against inherited sockets and active egress, including loopback, already-open descriptors and alternate IPC routes. New socket denial alone is insufficient.
4. Authenticated service-to-worker IPC: `SO_PEERCRED` must bind to expected trusted identities and scope; a nonce echoed in stdout is **not** authentication.
5. Descendant process containment and cleanup under forced timeout, service-manager failure or escape attempts; `KillMode=control-group` being requested is not itself a tested lifecycle guarantee.
6. A timed-out `systemd-run` client can leave unit cleanup **unverified**; it returns HOLD without asserting a terminated process tree. Independently test cgroup service cleanup.
7. User systemd manager restrictions depend on kernel unprivileged namespace support. Unavailable enforcement must return HOLD and cannot silently fall back to unsandboxed Python.

**Acceptance gate:** Have an independently configured disposable Linux host successfully run the fixture under a known service manager, capture exact unit property and OS-denial evidence, then add a separate fail-closed integration test using the actual fixed synthetic reviewer. Independent cybersecurity review and explicit owner authorization remain required for any future consequential use.

**Deployment status: `144 HOLD`.** No implementation in this experiment changes the live authorization boundary.