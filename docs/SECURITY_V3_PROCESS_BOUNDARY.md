# Security V3 — Process-separated, one-shot simulation worker

The worker in `offline_worker_v3.py` runs as a **separate Python process**
from the test caller. Requests cross a bounded, byte-oriented JSON channel
(`Connection.send_bytes` / `recv_bytes`); no untrusted `pickle.loads` or
callback deserialization is used for request content. The worker enforces the
preflight and signature at its own fixed synthetic dispatch site. It accepts
one message and then closes its channel.

Trusted public keys, policy, clock, and replay DB path are passed at trusted
process startup. Untrusted JSON must contain **exactly** `request` and
`approval`; attempts to pass authority/configuration fields, duplicate JSON
keys, oversized messages and invalid encoding result in `144 HOLD`.

Run `python -m unittest test_offline_worker_v3 -v` and
`python -m unittest discover -v` with pinned dependencies. Tests launch
real child processes and confirm SQLite replay persists across process restarts.

**Important: process separation is not OS-level security isolation.**
Both processes still share the host user's rights, filesystem and Python
runtime assumptions. The worker writes only its local verification database
and produces a synthetic result; it has no live side-effect capabilities.
This is not a production sandbox, authorizer, executor, or deployment permit.
Independent review, OS-specific least privilege, secure clock and trust
provisioning, secure IPC peer identity, storage protection, and real-world
cancellation/interlock design remain unimplemented.

The bounded intelligence evaluation in `bounded_learning_v1.py` remains
independent: no model weights, prompts or safety rules change automatically.
