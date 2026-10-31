# Security V5 — Trusted-parent wall-clock deadline (offline research)

Security V4 limits CPU, address space, file size and file descriptors inside the
worker. Security V5 adds a **trusted parent** wrapper that starts the existing
fixed simulation worker, sends bounded JSON bytes, enforces a monotonic
wall-clock deadline, and terminates then kills non-exiting workers. It accepts
no user-defined process target, no executable request, and no live capability.

A result counts as synthetic success only if a strictly validated worker reply
is received **and the child exits successfully within the deadline**.
Timeout, crash, malformed response and invalid input return `144 HOLD`.

Run: `python -m unittest test_offline_supervisor_v5 -v`.
The full Python 3.11 and 3.13 CI suites must also pass.

**Limits:** This does not isolate OS identities, networks or filesystems; a
hostile same-user process may still access them. The parent is assumed trusted,
and multiprocessing's trusted process bootstrap is not an untrusted IPC
protocol. Worker termination does not undo an external effect; therefore all
worker operations remain synthetic. Processes and descendants need an
OS-level containment strategy for stronger guarantees. No continuous loop
or automatic model changes are enabled.
