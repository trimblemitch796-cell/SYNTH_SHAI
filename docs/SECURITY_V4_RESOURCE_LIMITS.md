# Security V4: OS resource enforcement research milestone

The research worker now applies fixed, **Linux-kernel-enforced hard resource
ceilings** (CPU time, virtual address space, file size and open file
descriptors) inside its process *before* accepting untrusted JSON requests.

A trusted parent launches the worker with pinned keys, action policy, local
replay-database path and clock, none of which an incoming request can override.
The worker delegates to Security V3's one-shot, fixed synthetic dispatcher;
there are no live capabilities.

Run `python -m unittest test_offline_sandbox_v4 -v` or
`python -m unittest discover -v` on Linux. The regression tests start real
child processes and read back the OS limits. They also verify the process
cannot raise an enforced hard limit, then test signed approval, replay
and forged/forbidden requests. Unsupported OS resource APIs fail closed.

**DO NOT CONFUSE WITH AN ISOLATED EXECUTION SANDBOX.**
Rlimits constrain resources, not file reads, network connectivity, process
credentials, inherited environment, other local processes or tool authority.
Child-side setup also occurs after interpreter startup. A hostile Python
process can still escape this *application-level* workflow through capabilities
available to its OS user. No real execution has been wired up.

A future proper OS sandbox requires trusted *external* launch enforcement,
least-privilege identity, verified filesystem/network isolation, secure IPC
peer authentication, protection against resource exhaustion and independent
adversarial assessment. Keep real-world execution at `144 HOLD`.

Intelligence experiments remain limited to offline evaluation; no model is
trained or self-modified by this milestone.
