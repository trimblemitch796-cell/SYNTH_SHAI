# Security V3 — default-deny OFFLINE preflight (research)

This first milestone composes a trusted action allowlist, mandatory denylist,
and the already-tested Ed25519 signed approval verifier into one **non-executing**
function. It performs policy checks **before** consuming a valid one-use
approval nonce and request ID. A passing result is
`REVIEW_REQUIRED_NO_EXECUTION`, not permission to execute an action.

Only explicitly allowlisted actions are candidates. A built-in prohibition
set covers command execution, code deployment, fund transfers, physical
motion, messaging, cameras, microphones and deletion. A caller cannot
remove the mandatory prohibits through the policy object.

Run `python -m unittest test_offline_preflight_v3 -v` and then
`python -m unittest discover -v`.

**Limitations:** this is NOT a real execution boundary. A caller could
bypass this module entirely and invoke an external tool directly. This
module has no executor, OS sandbox, API boundary, host attestation,
protected policy source or distributed replay store. Host code and
configuration remain trusted. A future isolated execution service must
enforce a default-deny decision at the actual side-effect boundary,
with independent review before any consequential deployment.

No network calls, tool actions, autonomous loop or live permissions are added.
