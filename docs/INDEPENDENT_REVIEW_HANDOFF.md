# Independent security and safeguarding review — handoff package

**Status:** REVIEW REQUEST PREPARED, NOT INDEPENDENTLY REVIEWED.  
**Scope:** SYNTH_SHAI offline research prototype. No live deployment authorisation.  
**Prepared:** 25 October 2026. The assessor must record the exact reviewed Git commit.

## V4.1 execution-boundary independent-review addendum (1 November 2026)

**New primary review target:** exact immutable merge commit `bc62c9213ac5ea7bd3c1408ee20028f9d98bacb6` (merged PR [#69](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/69)). The older V3.1/PR #48 scope below is historical background and **does not supersede** this target. Record any newer reviewed commit separately.

**Internal evidence, not third-party evidence:** PR #69's head `e61eed65edc11f365d7c71edd57d906b67f59fc9` had passing GitHub Actions workflows: [verification](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/41254447316), [V3.1 CATHARSIS](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/41254447323), and [release security](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/41254447347). The verification logs reported 637 tests and the four new `test_v41_offline_boundary.py` checks passed. These results are for the **PR head**, not independent testing of the squash-merge SHA; a separate post-merge run is not established by the available evidence. Do not treat this as an audit or deployment authorization.

**Narrow V4.1 review entry point:** [SECURITY_V41_VALIDATION.md](SECURITY_V41_VALIDATION.md), [SECURITY_V4_RESOURCE_LIMITS.md](SECURITY_V4_RESOURCE_LIMITS.md), `offline_operator_admin_v2.py`, `offline_preflight_v3.py`, `offline_dispatch_v3.py`, `offline_worker_v3.py`, `offline_sandbox_v4.py`, `test_v41_offline_boundary.py`, `test_offline_sandbox_v4.py`, `test_offline_worker_v3.py` and relevant operator/replay tests.

**Independent reviewer questions (unresolved until independently evidenced):**
1. Does a trusted launch mechanism bind administrator and operator keys to authenticated humans, provide key rotation/revocation and prevent host-side substitution?
2. Can any malformed, forged, expired, replayed, revoked or raced approval produce any effect, including through process crash/timeout and unexpected worker exit?
3. Are worker identity, IPC peer, inherited descriptors, filesystem reads/writes, network connectivity and child-process creation constrained by operating-system enforcement? The current rlimits do **not** establish those boundaries.
4. Does the parent impose and enforce its own timeout/termination/reaping policies when the worker never replies? A child returning HOLD on handled errors is not complete failure containment.
5. Can multi-process or restarted components misuse the SQLite replay/revocation store or rewrite local audit records?

**Reviewer evidence protocol:** clone the exact target commit in a disposable offline Linux environment, inspect pinned dependencies before installation, use synthetic fixtures/test keys only, record command output, OS/kernel/Python versions, limits, and negative controls. Mark each guarantee **PASS / FAIL / UNVERIFIED**, distinguish own independent test observations from project CI, and report sensitive vulnerabilities privately through an owner-verified channel.

**Release status: `144 HOLD`.** Research tests and documentation can be merged; real-world/consequential execution remains unauthorized pending independent assessment, remediation, environment-specific safety review and a separate explicit human release authorization.

## Review baseline and smallest starting package

**Updated 27 October 2026:** start at commit `406440d32eb4aa4ffb3d2e0622aa831ef9600745` (PR #48 merged). Record any different assessed revision explicitly. [Release evidence reconciliation](RELEASE_SECURITY_CHECKLIST.md#pr-48-evidence-reconciliation--27-october-2026) links the same-commit CI logs: 442 tests, 33 offline scenarios exercised by tests, successful locked dependency installation and security jobs. These are project-maintained results, not independent review.

For the PR #48 trust-boundary change, begin with:
- This handoff, `THREAT_MODEL.md`, `TRUST_BOUNDARIES.md` and the release evidence reconciliation.
- `shai_v31_bridge.py`, `verification_v3.py`, `verification_v3_1.py` and `maniac/evidence.py`; trace callers in `maniac/supervisor.py`, `maniac/recovery.py` and `shai/twin.py`.
- `test_pinned_evidence_keys.py`, bridge/V3.1/replay tests and their imported fixtures. Use a full checkout to retain dependencies.
- `requirements.txt`, `requirements-lock.txt` and the CI workflows.
- For the benchmark-link fix: `maniac/benchmark.py`, `test_maniac_benchmark.py` and `FAIR_COMPARISON.md`.

Verify rejection of envelope-supplied keys, unissued/reused challenges, wrong hashes and missing trust. Distinguish MANIAC's in-memory issued-challenge registry from SQLite's durable accepted-challenge history. The direct bridge/CLI trusts the separately supplied expected challenge and hash; it does not itself issue challenges. Local configuration, host integrity, real source independence and human identity remain external trust requirements.

This focused entry point does not replace the wider security and specialist safeguarding scopes below.

## Reviewer independence and rules of engagement

Engage qualified external cybersecurity and, separately, child-safeguarding specialists without prior implementation responsibility. Agree scope, legal/ethical permissions, handling of sensitive findings, budget, deadline and conflict declarations **before** granting access to any nonpublic records. Public repository code can be inspected without operational credentials. Never share real child data, secrets or live credentials.

No penetration testing of third parties, accounts, infrastructure, or actual children. Use local/offline fixtures and controlled synthetic scenarios only. No physical actuation, bank transactions, automated reporting, camera/microphone access or operational model deployment.

Private vulnerability disclosures must use an owner-verified private channel; do not publish exploit details or credentials in issues or workflow logs.

## What the assessor should inspect

Start with the author's threat model, [THREAT_MODEL.md](THREAT_MODEL.md), which lists known gaps.

- [MISSION.md](MISSION.md): intended purpose and human control model.
- [TRUST_BOUNDARIES.md](TRUST_BOUNDARIES.md): verifier-held pinned keys, untrusted sensor inputs, caller-asserted operator identity/consent and audit assumptions.
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
