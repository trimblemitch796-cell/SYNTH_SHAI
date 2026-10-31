# SYNTH_SHAI — offline human-approval validation V1 (experimental)

This module is separate from production execution. It has **no actuator, network
or execution capability**. A successful signature returns
`VALIDATED_NO_EXECUTION`, **not** permission to perform an action.

The verifier receives trusted public keys and the database path from its trusted
host, not the request. Each signed approval binds one operator, exact request ID,
action, plan SHA-256, nonce and expiry. Only one use of a nonce **and of an exact request ID** is permitted per
local SQLite database. Re-signing the same request with another nonce does not
re-authorize it; a distinct request ID is needed for a new reviewed action. Expired, malformed, revoked, modified or replayed approvals
return `144 HOLD`. A trusted local administrator can revoke an operator; the
surrounding host must authenticate and protect that administrative call.

Run from repository root:
```bash
python -m unittest test_offline_approval_v1 -v
python -m unittest discover -v
```

**Limitations:** Host code, filesystem, operator-key configuration, clock and
revocation administrator are trusted. SQLite is not tamper-proof against the file
owner. No distributed replay or revocation propagation. Revocation and nonce
consumption are local to a database and do not prevent an already executed
action. This module does not implement a secure execution boundary; it must not
be wired directly to external tools or hardware. Independent review is pending.
