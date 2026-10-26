# Independent security and safeguarding review — handoff package

**Status:** REVIEW REQUEST PREPARED, NOT INDEPENDENTLY REVIEWED.  
**Scope:** SYNTH_SHAI offline research prototype. No live deployment authorisation.  
**Prepared:** 25 October 2026. The assessor must record the exact reviewed Git commit.

## Reviewer independence and rules of engagement

Engage qualified external cybersecurity and, separately, child-safeguarding specialists without prior implementation responsibility. Agree scope, legal/ethical permissions, handling of sensitive findings, budget, deadline and conflict declarations **before** granting access to any nonpublic records. Public repository code can be inspected without operational credentials. Never share real child data, secrets or live credentials.

No penetration testing of third parties, accounts, infrastructure, or actual children. Use local/offline fixtures and controlled synthetic scenarios only. No physical actuation, bank transactions, automated reporting, camera/microphone access or operational model deployment.

Private vulnerability disclosures must use an owner-verified private channel; do not publish exploit details or credentials in issues or workflow logs.

## What the assessor should inspect

Start with the author's threat model, [THREAT_MODEL.md](THREAT_MODEL.md), which lists known gaps.

- [MISSION.md](MISSION.md): intended purpose and human control model.
- [TRUST_BOUNDARIES.md](TRUST_BOUNDARIES.md): caller-supplied public keys, sensor inputs, operator text, consent and audit assumptions.
- [RELEASE_SECURITY_CHECKLIST.md](RELEASE_SECURITY_CHECKLIST.md): known review blockers, bounded CI/history scans and owner settings.
- [V31_RELEASE_VERIFICATION.md](V31_RELEASE_VERIFICATION.md): replay and verification evidence limits.
- [MANIAC_SUPERVISOR.md](MANIAC_SUPERVISOR.md), [V25_TRI5.md](V25_TRI5.md): offline supervisor and safeguarding advisory scope.
- Source and tests: `verification_v3.py`, `verification_v3_1.py`, `shai_v31_bridge.py`, `ushai_catharsis.py`, `maniac/`, `v25_tri5.py`, `shai/`, corresponding `test_*.py`.

**Medical-adjacent code:** `synth_shai_doctor/` (AAA Doctor V1) is a simulation-only rule layer for abdominal aortic aneurysm danger signs. It accepts synthetic cases only. It is **not a medical device**, makes no diagnosis or dispatch, and needs review by a qualified clinician (plus regulatory and privacy review) before any real-world use.

## Reproduction on an isolated checkout

1. Record reviewer, system/platform, repository URL, **exact immutable commit SHA**, Python version, dependency hashes and date.
2. Inspect `requirements-lock.txt` and CI workflows before running external dependency installers.
3. Within a disposable local environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-lock.txt
python3 -m unittest discover -v
python3 -m maniac.simulation
```

4. Record command results, failures, test count and exact relevant GitHub Actions URLs for the same revision. Any inaccessible dependencies or failed scans are **incomplete evidence**, not a pass.
5. Do not use prior CI successes as evidence for an untested new revision.

## Review questions and failure-oriented scenarios

| Area | Attempt to falsify | Required observation |
| --- | --- | --- |
| Identity/consent | Substitute operator text, expire consent mid-request, swap request identifiers | Unauthenticated or out-of-scope action cannot be authorised |
| Evidence provenance | Supply two colluding keys, forged labels, stale sensor reports, contradictory values | Caller labels alone are never treated as independent truthful sources |
| Replay | Duplicate challenge across threads/processes; reopen, copy, replace or delete SQLite store | Precise statement of protected single-store scope and unprotected cross-device cases |
| Runtime safety | Inject NaN/Infinity, missing data, heartbeat loss, sensor freeze, faults during recovery | Fail-closed HOLD/SAFE_LOCK with no unapproved side effects |
| Audit integrity | Edit, truncate, reorder, replace or regenerate hash-chain records; remove checkpoint | Tampering detection boundaries and remaining host/checkpoint trust documented |
| Ethical review | Use urgent social pressure and confident but unevidenced claims; innocuous borderline requests | HOLD is not overridden; harmless work is not reflexively blocked |
| Safeguarding | Invalid synthetic flags, ambiguous evidence, false alarms, urgent advice during HOLD | No asserted child detection, no automatic reporting, urgent-help pathway preserved |
| Supply chain | Audit committed pins, GitHub Action permissions, dependency advisories, historical credential exposure | Exact-scope evidence, unresolved findings and owner-configured controls clearly distinguished |

## Comparison study (separate from security sign-off)

Benchmark three matched implementations on pre-registered, held-out synthetic cases: (A) baseline safeguards, (B) independent safety-supervisor design, (C) integrated SYNTH_SHAI. Report harmful-action misses (with severity), false-positive rate, legitimate-task completion, consent-policy violations, detection latency, recovery integrity, run cost and confidence intervals. Do not choose only cases that favour this architecture. Report sample-size limitations and any untested threat class. **No superiority claim without comparable evidence and independent scrutiny.**

## Expected independent deliverables

- Signed or attributable assessment with reviewer expertise, conflict statement, exact commit/scope and method.
- Findings with unique IDs, severity, reproducible synthetic steps, affected files and evidence.
- Explicitly tested **and untested** trust assumptions and attack surfaces.
- Remediation plan with owner and verification criteria; independent retest of significant fixes.
- Separate safeguarding assessment of purpose, false alarms, escalation guidance and privacy.
- Release recommendation clearly distinguishing offline research, narrow low-risk pilot and consequential production use.

## Owner actions before any consequential deployment

- [ ] Confirm branch protection, required independent approval and CI/security checks on `main`.
- [ ] Enable and test private vulnerability reporting and verify contact method.
- [ ] Commission independent cybersecurity and specialist safeguarding reviews.
- [ ] Specify authenticated human approval, binding to exact request/scope and trusted evidence-source enrolment.
- [ ] Design compromised-host, checkpoint custody, distributed replay, revocation and incident response.
- [ ] Resolve findings and document explicit deployment-specific hazard and legal review.
- [ ] Record the authorised human release decision only after all applicable gates are satisfied.

**Release disposition: 144 HOLD.** Passing existing tests or completing this handoff document is not certification, proof of safety, or permission to deploy.
