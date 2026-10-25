# SYNTH_SHAI V3.1 — Build Status
_Last reviewed: 25 October 2026 (Australia/Brisbane)_

## Scope
This is an **offline software-prototype** progress record, not a declaration that the entire SYNTH_SHAI vision, a physical MANIAC chip, or a public AI service is complete.

Progress is recorded as implemented milestones and outstanding review gates below. There is no validated percentage-complete or delivery-time estimate for the wider research program.

## Verified repository milestones
- PR #2: V3.1 evidence-gate work merged.
- PR #5: offline verification bridge merged.
- PR #8: public research-beta contribution/security documentation merged.
- PR #11: MANIAC supervisor core and USHAI CATHARSIS gate merged.
- PR #12: offline MANIAC monitor system merged.
- PR #13: supervisor numeric-input and recovery-ID hardening merged (9 adversarial tests).
- PR #14: offline MANIAC CHECK EVIDENCE merged.
- PR #15: MANIAC_SIMULATION offline fault injector merged.
- PR #16: 555000 TRIANGULATE + 444000 VERIFY / HUMAN APPROVAL (CONSEQUENCE REVIEW) merged.
- PR #17: offline V25 TRI5 child-safeguarding advisory gate merged.
- PR #18: MANIAC–USHAI–V25 TRI5 synthetic integration tests merged.
- PR #19: V3.1 concurrent / durable replay regression tests and release evidence matrix merged.
- PR #20: clean-up (docs consistency, read-only result objects, de-duplicated VERIFY reasons) merged.
- PR #22: step 6, which covers 1301133 BUILD / REPAIR / REFRAME, 666000 RECOVERY, 222000 RE-OBSERVE, 111000 COMPARE / LEARN, 999000 AUDIT, Δ BALANCE and `run_loop`, merged.
- PR #23: Super Tool V1 offline ASK / CHECK / BUILD starter merged.
- Step 7: SHAI digital twin + ELO-ECTRIC power model are present on `main`. Software only, illustrative numbers, **not hardware-ready**.

## Offline completion work in this change
- [x] Optional local SQLite audit storage, verified on reopen, with atomic appends and stale-writer rejection.
- [x] Optional V25 TRI5 assessment in `run_loop`, before any recorded human decision; a prior HOLD is preserved.
- [x] Regression coverage for invalid power inputs and simulated motion exceeding the consent window.
- [x] Keep human `REJECTED` decisions conservative: `UNBALANCED` and `144 HOLD`.

These changes are proposed for maintainer review; this record does not claim they have merged or that a new CI run has passed.

## Reproduce verification
```sh
python3 -m unittest discover -v
python3 -m maniac.simulation
```
Local verification on 25 October 2026 passed **279 tests** and **33/33 simulation scenarios**. The baseline (`84bf0b7`, PR #24 merged) passed 243 tests before these changes. Re-run on the revision under review; local results and GitHub Actions results are separate evidence.

## Next step
Review the completed offline changes, then obtain independent outside review (see issue #21). Persistent audit storage and V25 TRI5 loop integration are now implemented as opt-in prototype features. Neither establishes trusted sensor/consent provenance, independent safeguarding capability or production readiness. See [MANIAC_SUPERVISOR.md](MANIAC_SUPERVISOR.md) for usage and audit limitations.

## Public beta audit (issue #9)
- **Audited:** commit `ef1ffd2` on 25 October 2026. The audit was read-only.
- **Secrets:** gitleaks found nothing across all 83 commits on every branch and PR. Pattern searches found no keys, tokens, passwords, `.env` files, phone numbers or addresses in any file.
- **Files:** no large or binary files. One old `test_results.txt` (finance test output only) was removed in `445b660`.
- **CI:** read-only token permissions, no `pull_request_target`, no secrets, and test failures fail the job. Actions are now pinned to commit SHAs, and Dependabot config has been added.
- **Still pending, because Mitch must change these GitHub settings himself:**
  - [ ] branch protection on `main`
  - [ ] private vulnerability reporting
  - [ ] Dependabot alerts and security updates
  - [ ] commit email privacy: the personal email appears as the author on past commits

## Outstanding release gates (144 HOLD)
- [ ] Complete the broader concurrency and replay assessment. Local single-database duplicate/reopen cases are tested in PR #19; the optional audit store adds local transaction and stale-writer checks. Cross-device replay and distributed audit integrity are not established.
- [x] MANIAC + V3.1 evidence-bridge synthetic integration scenarios exist (`python3 -m maniac.simulation`, including full-loop recovery and SHAI twin). Re-run on the reviewed revision; USHAI is covered only by its fixed baseline input.
- [ ] Review trust-key provisioning, source independence and approval/consent provenance.
- [ ] Review public repo and git history for secrets, private data and licensing.
- [ ] Obtain independent security and hazard review before consequential applications.

## Mandatory boundaries
- `144 HOLD` for faults, missing or contradictory evidence, replay, and unauthorized requests.
- `444000` is verification and human review **not deployment authorization**.
- No network operations, external account access, money movement, physical actuation or autonomous authority granted by these prototypes.
- Human choices and approved scope remain external to test-result validity.

> Connection before control. Truth before belief. Repair before rebuild.
