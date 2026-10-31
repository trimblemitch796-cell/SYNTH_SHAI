# SYNTH_SHAI Security V3 — fixed simulation dispatch

Security V3 now has two distinct local modules:

1. `offline_preflight_v3.evaluate_preflight` applies mandatory denylist,
   trusted action allowlist, and Ed25519 one-use approval verification.
2. `offline_dispatch_v3.dispatch_simulation` is the **sole entry point into
   a fixed simulated effect**, with the policy and signature gate performed
   in the dispatch path. It accepts no executable callback or handler.

Only `synthetic_review` is implemented, returning
`SIMULATED_REVIEW_ONLY` and a synthetic, immutable output. Invalid signatures,
denied actions, expired approvals, replayed signatures and invalid storage
return `144 HOLD` without a simulated effect.

Run:
```bash
python -m unittest test_offline_dispatch_v3 -v
python -m unittest discover -v
```

### Trust-boundary warning

This demonstrates **in-process enforcement for one static simulated
operation**. It is **NOT actual OS isolation**, production authorization,
a hosted service, a hardware interlock, or general-purpose real-world action
enforcement. Code running in the same process can bypass or replace Python
functions. Real-world tools are not integrated and must remain disabled.
The next milestone requires a separately isolated, trusted execution service
which owns its capabilities, validates authorization within its boundary,
implements reliable cancellation and audit, and passes independent tests.

The source code must not be described as autonomous growth or superintelligence.
