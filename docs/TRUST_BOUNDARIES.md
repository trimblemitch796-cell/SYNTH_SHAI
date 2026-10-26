# Offline verification trust boundaries

This is an internal engineering review of the offline prototype, not an independent
security assessment. It records what the implementation checks and what a future
trusted integration would still have to establish.

## Actors and inputs

The trusted integration supplies pinned public keys and the local database path separately from untrusted envelopes. After PR #48, MANIAC issues single-use challenges bound to an expected report digest; the direct bridge/CLI instead requires the trusted caller to supply the expected digest and challenge. Untrusted inputs still include candidate reports, sensor observations, consent assertions and operator text. The prototype does not authenticate that caller or attest the host. An
independent reviewer must consider malicious or mistaken callers, compromised keys,
conflicting observations, stale inputs, storage faults and host compromise.

| Boundary | Current check | Required trust outside the prototype |
| --- | --- | --- |
| Report → signed evidence gate | Strict fields, report digest, Ed25519 signatures, challenge and source labels | Provision keys separately from untrusted envelopes; establish key ownership, revocation, rotation and actual observer independence. Two labels/keys do not prove two independent people or sensors. |
| Candidate → replay database | Persistent local SQLite file, expected schema, transactional challenge insertion, duplicate rejection, failure to HOLD | Protect the path, database and host. Retain one store for its intended scope; replacing/deleting a valid store can erase replay history. No cross-device coordination is established. The store path is trusted configuration set when the Supervisor/ShaiTwin is constructed; requests cannot select it (a request `db_path` is refused, giving HOLD). |
| Sensor/consent assertions → MANIAC | Finite values, ranges, freshness, contradictions, declared permitted action and expiry | A trusted adapter must bind request, observations, consent and signed evidence to the same canonical action, limits, identity and lifetime. Caller assertions do not establish the truth of observations or consent. |
| Operator text → human decision | Explicit APPROVED/REJECTED and nonempty operator/reason fields | Authenticate the human and bind the decision to the exact reviewed request. A supplied string is not proof of identity or authority. |
| Runtime observations → time checks | Finite clock and policy values; simulated consent rechecked during motion | Establish a trustworthy time source, clock rollback behavior and cancellation semantics for any future real integration. |
| Loop → audit store | Verified local chain, transactional append, stale-writer rejection, optional independent head checkpoint | Hashes are unkeyed. Protect checkpoints separately; suffix deletion or fully recomputed history cannot be authenticated by internal consistency alone. |
| Risk flags → V25 TRI5 | Bounded advisory composition, preserving an upstream HOLD; urgent advice exposed without approval | Qualified humans must determine facts and lawful next steps. The flags are not a trained detector, an age check, verified allegations or automated reporting. |

## Failure and authority boundaries

Invalid evidence, replay/storage failure and unresolved gate failures produce HOLD.
REVIEW_REQUIRED/HUMAN_REVIEW only requests human review. Machine
`approval_granted` remains false. The signed-evidence scope is a report/revision/
challenge; it does not authenticate every later runtime input or a human operator.

Local SQLite protects a single retained database under its host assumptions. It is
not protection against an administrator changing files, compromise of the Python
process, malicious replacement of all trusted configuration, or distributed replay.
The current test keys and synthetic sources are not production trust anchors.

## Before a consequential integration

- Specify canonical request/evidence/consent binding and authenticated operator roles.
- Design trusted key provisioning, independent-source criteria, rotation/revocation
  and compromised-key response outside untrusted input envelopes.
- Specify storage ownership, retention, file-loss recovery, checkpoint custody,
  clock behavior and cross-device scope. Test failure and restart behavior.
- Obtain independent review for the intended domain and make an explicit human
  release decision. Keep external side effects disabled until that separate work
  is accepted.

The current release disposition and remaining owner actions are recorded in
[RELEASE_SECURITY_CHECKLIST.md](RELEASE_SECURITY_CHECKLIST.md).
