# Independent security and safeguarding review — handoff package

**Status:** REVIEW REQUEST PREPARED, NOT INDEPENDENTLY REVIEWED.  
**Scope:** SYNTH_SHAI offline research prototype. No live deployment authorisation.  
**Prepared:** 25 October 2026. The assessor must record the exact reviewed Git commit.

## Current assessor entry point — 2 November 2026

**Exact current review candidate:** `93708f8ae46a9d2f772adce4ead7215ca7270af2` (`main`, [PR #72 squash merge](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/72)). Freeze this SHA for the first review; if a later PR merges, separately record the new revision and retest it. The historical PR #48 starting point below is not the current baseline.

**Author-maintained evidence for this exact revision** (NOT an audit):
- [GitHub verification](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/41407397764): 654 tests passed on Python 3.11; separately 654 on Python 3.13; nine V4.1 parent lifecycle regressions in each.
- [V3.1 CATHARSIS](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/41407397810): 15 tests passed (included in full discovery).
- [Release security](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/41407397822): dependency and reachable-history jobs passed; scope-bounded only.
- [Verified inventory](VERIFIED_CORE.md) and [release checklist](RELEASE_SECURITY_CHECKLIST.md) give historical and exact-SHA distinctions.

**Focus for independent technical reviewer:** `offline_parent_v41.py`, `offline_sandbox_v4.py`, `offline_worker_v3.py`, `offline_dispatch_v3.py`, `offline_preflight_v3.py`, `offline_approval_v1.py`, `offline_operator_admin_v2.py`, `test_v41_parent_lifecycle.py`, `test_v41_offline_boundary.py`; also inspect the threat model, trust boundaries and [V5 isolation acceptance contract](V5_OS_ISOLATION_CONTRACT.md). Independently try to falsify the claims: hang/crash/partial reply, one-use replay after crashes, parent process-start stall, descendants, OS identity, filesystem, network, IPC peer spoofing, key custody, clock and SQLite tampering. Where a control is absent, mark **UNVERIFIED/NOT IMPLEMENTED**, not PASS.

**Separate safeguarding specialist:** review V25 TRI5 / USHAI only as offline advisory artifacts; assess false positives/negatives, child privacy, consent, escalation limits and claims made to users. No use of live child data or participation by minors.

**Proposed engagement:** volunteer/open-source scoped review or fixed-price assessment by independently qualified reviewers, contingent on their acceptance. Request independence/conflict declaration, scope, timeframe, deliverable/report, findings severity, safe reproduction and coordinated private disclosure. Do not claim anyone has agreed, been booked, or completed an assessment.

**Safe reproduction:** isolated disposable Linux host, locked dependencies from `requirements.txt`; `python3 -m unittest discover -v`, `python3 -m unittest -v test_v41_parent_lifecycle test_v41_offline_boundary`; record exact SHA, OS/kernel, Python version, actual observed failures and timestamps. No production credentials, actual children, live networks, banking, medical advice or physical actuation.

**Still blocked:** neither Python child-side rlimits nor parent direct-PID cleanup establish full OS sandboxing; trusted external startup deadline, process-tree containment, filesystem/network restriction, dedicated identity and authenticated IPC are open [issue #73](https://github.com/trimblemitch796-cell/SYNTH_SHAI/issues/73). `144 HOLD` remains for consequential use.

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
