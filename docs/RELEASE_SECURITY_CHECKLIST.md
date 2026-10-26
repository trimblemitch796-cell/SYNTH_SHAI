# Release and security checklist

## PR #48 evidence reconciliation — 27 October 2026

Evidence baseline: `406440d32eb4aa4ffb3d2e0622aa831ef9600745`, the merge of [PR #48](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/48) on 26 October 2026. These results apply to that immutable revision; later changes need their own checks.

| Evidence | Observed result | Boundary |
| --- | --- | --- |
| [Verification run 40301085939](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40301085939) | 442 tests passed; includes the ten pinned-key regressions, all-scenarios-pass test and benchmark/report equality test | Project-maintained CI, not independent validation |
| [V3.1 run 40301085852](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40301085852) | 15 V3.1 tests passed | This subset is included in discovery; do not add it to 442 |
| Locked dependency installation | CI installed cryptography 50.0.2, cffi 2.1.1 and pycparser 3.12 under Python 3.11.17 | Supersedes pending-CI wording for this baseline; historical local results used a different environment |
| [Release-security run 40301085774](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40301085774) | dependency-advisories and reachable-history-secrets jobs succeeded | Known-advisory and fetched-history scope only |
| 33 simulation scenarios | Passing CI tests exercise all 33 scenarios; benchmark totals remain 29 expected stops and 4 expected allows | Author-written, offline fixtures; not independent evidence of superiority |
| Independent review | Handoff prepared; PR #48 has no submitted reviews at this check | No independent assessment established; consequential deployment remains **144 HOLD** |

The table above supersedes pending-CI statements for this baseline only. Historical entries below retain their original dates and scope. The branch API currently reports `main` protected with four required checks; this does not independently establish reviewer-approval settings, bypass restrictions or private-reporting availability.


## Status reconciliation — 26 October 2026 (issues #9, #10 and #21)

This section supersedes *only the historical status entries* below where later evidence has changed; retain the original audit details as a dated record.

- **#9 public beta:** PR #26 merged with reported passing exact-head GitHub Actions: [verification](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40154046508) (288 tests), [V3.1 CATHARSIS](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40154046555), and [release security](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40154046634) (bounded history and dependency scanners). PR #27 merged action pinning, Dependabot configuration and scope disclaimer. `docs/BUILD_STATUS.md` records branch protection and private vulnerability reporting as enabled on 25 October. These records do **not** verify CI for the latest `main` commit. Recheck current branch settings and latest exact-head runs before closing #9. Dependabot alert/update settings, personal commit email history, privacy review, and release-specific approvals require owner verification.
- **#10 adversarial challenge:** Existing replay, malformed-input, consent and HOLD regressions cover named synthetic cases; no exhaustive adversarial/security guarantee is established. Leave open for third-party reproducible counterexamples, including cross-host replay, compromised storage, colluding evidence sources, corrupted audit checkpoints, and harmful/benign classification calibration. Sensitive findings belong in private vulnerability reporting.
- **#21 independent review:** PR #33 merged the [assessor handoff](INDEPENDENT_REVIEW_HANDOFF.md). That is preparation, **not** completion of an external cybersecurity or child-safeguarding assessment. Keep open until independent written reports, remediation and retests exist. No reviewer engagement has been verified here.
- **Current release gate:** `144 HOLD` on consequential deployment. Owner must confirm settings, external reviewer appointments and explicit `444000` release decision. Do not close any of the above issues based solely on this documentation update.


Reviewed 25 October 2026. Baseline: `main` at
`ef1ffd22c210614dffaa9087b695b21f9efab5b7` (PR #25 merged).

**Release decision: HOLD for consequential deployment.** The completed checks
below support continued offline research. They are not an independent assessment,
a safeguarding certification, or permission to operate hardware or live accounts.

## Evidence and disposition

| Check | Evidence | Disposition |
| --- | --- | --- |
| Main build after PR #25 | [Verification run 40152624706](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40152624706): success; 279 tests; Python 3.11; cryptography 46.0.7 | Confirmed for the named baseline. Recheck the new PR/head. |
| Visible branch-history inventory | Five branch heads, 83 reachable commits, 63 distinct trees, 150 distinct file blobs; history reached a root on each branch | Completed for those observed branch heads. Tags and unreachable/deleted objects were not available through the connection. |
| Targeted credential-pattern scan | Exported historical blobs checked against Git blob hashes and scanned for common private-key/token/credential shapes; no matches | Bounded preliminary check. Specialist full-history scanning remains a separate CI check; no claim that all private data or unknown credential formats are absent. |
| License and dependency notices | MIT project notice present; direct/transitive Python dependency license metadata reviewed; see [notices](../THIRD_PARTY_NOTICES.md) | Source-level check completed. Review all binary/bundled notices before distributing artifacts. |
| Dependency advisories | Published metadata identifies advisories affecting the baseline cryptography package. This change updates its pin and adds dependency-audit CI | Advisory results are time-sensitive. Require the new dependency audit to pass; do not ignore findings to obtain a green result. |
| Workflow review | Read-only contents permission, pinned action commits, checkout credentials not retained, shared locked dependency input, separate history/dependency checks | Implemented in this change; inspect exact-head CI before merge. |
| Evidence/replay failure paths | Local synthetic regressions for persistent replay storage, malformed inputs, finite consent/clock/policy values, and bridge failure handling | 288 local tests and 33/33 simulation scenarios pass. Local Python is 3.12.14 with cryptography 50.0.0, cffi 2.1.1 and pycparser 3.0; exact lock installation was blocked by the workspace proxy, so CI must verify it. |
| Trust-key provisioning and source independence | [Trust boundary review](TRUST_BOUNDARIES.md) | Documented; production trust establishment is not implemented or validated. |
| Private vulnerability reporting | Public security pages did not expose a report button; the connection cannot read or change the administrative setting | Unconfirmed. Owner must enable/confirm the private channel before soliciting sensitive reports. |
| Main-branch protection | Branch listing reports `protected: false`; repository rulesets list is empty; detailed protection read returns permission denied | Owner action required: configure and verify review/check requirements. No settings were changed by this review. |
| Independent cybersecurity and safeguarding assessment | [Issue #21](https://github.com/trimblemitch796-cell/SYNTH_SHAI/issues/21) remains open | Required for consequential applications. This assistant's review does not satisfy independence. |

The original [release checklist (#9)](https://github.com/trimblemitch796-cell/SYNTH_SHAI/issues/9)
and [adversarial testing invitation (#10)](https://github.com/trimblemitch796-cell/SYNTH_SHAI/issues/10)
remain open. This document records bounded evidence rather than closing those issues.

## Reproduce the engineering checks

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-lock.txt
python3 -m unittest discover -v
python3 -m maniac.simulation
```

The security workflow runs the dependency advisory audit and redacted history
scanner. Inspect its job result on the exact candidate commit. A scanner/network
failure is an incomplete check, not evidence of a clean result. Reports containing
possible secrets must remain private; do not paste them into public issues or logs.

History scope is the refs available at scan time. Deleted branches, inaccessible
forks, attachments, Git LFS objects and previously leaked copies need separate
consideration. No exposed credential was identified in the targeted scan, so no
credential rotation or history rewrite was performed.

## Owner and independent-review actions

1. Enable or confirm **Private vulnerability reporting** in repository Settings →
   Security and quality → Advanced Security. Confirm the **Report a vulnerability**
   button appears on the Advisories page. Keep sensitive findings out of public issues.
2. Configure protection for `main`: require pull requests, approving human review,
   passing verification and security jobs, and resolved review conversations; restrict
   force pushes/deletion and decide explicitly whether administrators may bypass rules.
3. Arrange the cybersecurity and separate safeguarding assessments scoped in #21.
   Refresh the assessed commit, agree confidentiality and deliverables, address findings,
   and record the human release decision. No reviewer was contacted by this task.
4. Define a trusted key/consent/request adapter and its threat model before extending
   the offline prototype's authority. Complete distribution-specific license and binary
   provenance checks before shipping a packaged artifact.

GitHub references: [private reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository),
[branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

## Acceptance boundary

Source availability, local tests and project-maintained CI do not demonstrate that
caller assertions are true or that a human is authenticated. Signatures establish
possession of provisioned keys, not independent observers or real-world consent.
SQLite replay/audit protection assumes a protected host and retained local files.
Human rejection and unresolved evidence stay HOLD. No network-enabled application,
money movement, physical actuation, surveillance or automatic reporting is enabled.
