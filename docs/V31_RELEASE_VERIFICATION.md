# V3.1 Release Verification — Evidence Matrix
_25 October 2026. Offline research prototype; not a production release certificate._

## Scope and status
SYNTH_SHAI V3.1 comprises the offline evidence gate, MANIAC supervisor, USHAI CATHARSIS gate and V25 TRI5 advisory safeguarding gate. Successful automated tests must not be interpreted as real-world safety approval, independently verified safeguarding capability or permission for physical/network actions.

## Evidence confirmed
- PR #13 MANIAC input-hardening merged following two successful GitHub Actions workflows.
- PR #17 offline V25 TRI5 safeguarding advisory gate merged after successful verification workflows.
- PR #18 MANIAC–USHAI–V25 TRI5 synthetic integration tests merged at commit `17c29bb7048d27e5ac1f3c9e4748bc0064e7aab0` after both configured workflows succeeded.
- Proposed on this branch: concurrent duplicate-challenge, post-commit replay and corruption regression tests. **Only mark these as passing after GitHub Actions confirms the exact branch/head commit.**

## Concurrency/replay test boundaries
- SQLite `BEGIN IMMEDIATE` and a unique challenge key should prevent duplicate successful accepts *within one local shared database*. Multi-threaded test validates one accepted `REVIEW_REQUIRED` and remaining `144 HOLD` outcomes.
- Additional process/reopen test verifies persisted local replay state.
- **Not established**: cross-device replay coordination, distributed consensus, resistance to malicious DB replacement or host compromise, production key provenance, independent source identities, real human consent.

## Security review findings and open work
- Trusted public key provisioning and source independence are caller responsibilities; mock signed records do not authenticate humans.
- MANIAC and USHAI rely on caller-provided assertions; real sensor, consent and harm evidence require a trusted collection and evaluation design.
- The V25 TRI5 risk flag classifier does not detect exploitation independently; trained humans and lawful safeguarding pathways remain necessary.
- GitHub Actions is project-maintained CI; it is **not an independent security assessment**.
- A complete repository/history secret scan, independent penetration review, external safeguarding review and jurisdiction-specific legal assessment have **not been evidenced**.
- Offline libraries do not constitute a hosted public assistant or protective service.

## Final release gate
**Decision: 144 HOLD on consequential or autonomous public deployment.** Public research-source access, bounded local tests and feedback may continue. Reassess only after signed-off requirements, tests, independent review and explicit human authorization (444000).

**Verification ≠ Permission. Capability ≠ Authority.**
