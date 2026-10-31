# SYNTH_SHAI SECURITY V2 — signed operator revocation (research prototype)

This milestone adds offline, Ed25519-signed revocation envelopes bound to
an administrator ID, operator ID, unique nonce, expiry and explicit operation.
Administrator public keys must be **pre-pinned by a trusted host**; an incoming
envelope cannot nominate its own authority. A verified transaction atomically
records a one-use administrator nonce and a local operator revocation.

The old unauthenticated `revoke_operator` entry point now **fails closed**,
rather than writing a revocation. This is intentionally a breaking change for
callers that previously assumed the local method itself authenticated humans.

Test:
```bash
python -m unittest test_offline_operator_admin_v2 -v
python -m unittest discover -v
```

**Limitations:** Python code in the same trusted process can still access
internal database functions or modify files. This is not an isolation boundary,
is not distributed, does not secure clocks or key provisioning, and cannot
undo actions already executed. There are no live user accounts, login flows,
hardware permissions, production operations or outbound network calls.
`REVOKED_NO_EXECUTION` means only that the local revocation was recorded.
Do not connect this module to real-world tools without a separately verified
execution controller and independent adversarial review.
