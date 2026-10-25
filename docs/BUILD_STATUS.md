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
- AAA Doctor V1 (`synth_shai_doctor/`, Mitch's package): proposed. **Simulation-only, synthetic data only, not a medical device, needs external clinical review.**
- Review fix (HIGH): the V3.1 replay database is now fixed by trusted configuration (`Supervisor(replay_db=...)` / `ShaiTwin(replay_db=...)`). Request provenance must be exactly `{"envelope"}`; a request-supplied `db_path` is refused (144 HOLD), and with no configured store provenance always HOLDs.
- Review fix (HIGH): SHAI twin human approval is bound to the exact motion plan. It must carry `plan_sha256 = plan_digest(plan)` (build with `approval_for(plan, ...)`), is re-checked right before motion, and is single-use. A mismatch, an ID-only approval or a reused approval gives 144 HOLD with no motion.
- Review fix (MEDIUM): the `HUMAN REVIEW` audit entry now records who decided. Its hashed `detail` is canonical JSON `{operator_id, reason[, plan_sha256]}` and is stored in the opt-in SQLite audit too. A missing or empty operator_id is refused, giving 144 HOLD, never an anonymous decision. Older entries (detail = reason text) still verify.
- Review fix (MEDIUM): only a `VerifyResult` issued by the real 444000 VERIFY path (`consequence_review`) can record a human decision or reach Δ BALANCE. A hand-built `VerifyResult("HUMAN_REVIEW")`, or a human decision not recorded on that result, gives UNBALANCED / 144 HOLD. This is an in-process guard, not a cryptographic seal.
- Review fixes (LOW):
  - A recorded human decision is tamper-evident: an `object.__setattr__` overwrite or field edit is detected, giving 144 HOLD, and re-recording is refused.
  - The SQLite audit keeps a count/head anchor, so deleting tail rows is detected on load without `expected_head`. Older databases are anchored on first open.
  - AAA Doctor `Review` rejects `human_approval_required` not True, `diagnosis_made` not False and `autonomous_dispatch` not False (ValueError).
- Fair comparison (offline, author-written, not independently reviewed): `python3 -m maniac.benchmark` runs all 33 scenarios through SYNTH_SHAI, an E-stop + watchdog baseline and a human-approval-gate baseline, and writes [FAIR_COMPARISON.md](FAIR_COMPARISON.md). No superiority claim; see its limitations.

## Offline completion work (PR #25 merged)
- [x] Optional local SQLite audit storage, verified on reopen, with atomic appends and stale-writer rejection.
- [x] Optional V25 TRI5 assessment in `run_loop`, before any recorded human decision; a prior HOLD is preserved.
- [x] Regression coverage for invalid power inputs and simulated motion exceeding the consent window.
- [x] Keep human `REJECTED` decisions conservative: `UNBALANCED` and `144 HOLD`.

PR #25 merged at `ef1ffd22c210614dffaa9087b695b21f9efab5b7`. Its post-merge verification workflow passed with 279 tests. The next security-hardening change adds nine more local regressions, dependency locking, CI history/advisory scans and an evidence-based release checklist; its exact-head CI must be checked separately.

## Reproduce verification
```sh
python3 -m unittest discover -v
python3 -m maniac.simulation
```
Local verification on 26 October 2026 (with the fair-comparison benchmark applied) passed **431 tests** and **33/33 simulation scenarios**. The security-hardening candidate on 25 October 2026 passed 288 tests. The PR #25 baseline passed 279 tests; PR #24 had 243. The local run uses cryptography 50.0.0; exact-lock installation must be validated by CI because workspace package networking is unavailable. Re-run on the revision under review; local results and GitHub Actions results are separate evidence.

## Next step
Review the release/security hardening and exact-head CI, enable/confirm private reporting and branch protection, then obtain independent outside review (see issue #21 and [the release checklist](RELEASE_SECURITY_CHECKLIST.md)). Persistent audit storage and V25 TRI5 loop integration are now implemented as opt-in prototype features. Neither establishes trusted sensor/consent provenance, independent safeguarding capability or production readiness. See [MANIAC_SUPERVISOR.md](MANIAC_SUPERVISOR.md) for usage and audit limitations.

## Public beta audit (issue #9)
- **Audited:** commit `ef1ffd2` on 25 October 2026. The audit was read-only, and it complements [the release checklist](RELEASE_SECURITY_CHECKLIST.md).
- **Secrets:** gitleaks found nothing across all 83 commits on every branch and PR. Pattern searches found no keys, tokens, passwords, `.env` files, phone numbers or addresses in any file.
- **Files:** no large or binary files. One old `test_results.txt` (finance test output only) was removed in `445b660`.
- **CI:** read-only token permissions, no `pull_request_target`, no secrets, and test failures fail the job. Actions were SHA-pinned in PR #26. A weekly Dependabot config is added in PR #27.
- **GitHub settings** (read via the API on 25 October 2026):
  - [x] branch protection on `main`: requires a PR and 4 checks
  - [x] private vulnerability reporting: enabled
  - [ ] Dependabot alerts and security updates: still off, and Mitch must turn them on
  - [ ] commit email privacy: the personal email appears as the author on past commits, and Mitch can hide it for future commits

## Outstanding release gates (144 HOLD)
- [ ] Complete the broader concurrency and replay assessment. Local single-database duplicate/reopen cases are tested in PR #19; the optional audit store adds local transaction and stale-writer checks. Cross-device replay and distributed audit integrity are not established.
- [x] MANIAC + V3.1 evidence-bridge synthetic integration scenarios exist (`python3 -m maniac.simulation`, including full-loop recovery and SHAI twin). Re-run on the reviewed revision; USHAI is covered only by its fixed baseline input.
- [ ] Review trust-key provisioning, source independence and approval/consent provenance.
- [ ] Finish the release content/history review: a targeted scan of 150 verified blobs across five visible branches found no common credential patterns; specialist history CI, private-record review and distribution-specific licensing remain distinct checks. See [the release checklist](RELEASE_SECURITY_CHECKLIST.md).
- [ ] Obtain independent security and hazard review before consequential applications.

## Mandatory boundaries
- `144 HOLD` for faults, missing or contradictory evidence, replay, and unauthorized requests.
- `444000` is verification and human review **not deployment authorization**.
- No network operations, external account access, money movement, physical actuation or autonomous authority granted by these prototypes.
- Human choices and approved scope remain external to test-result validity.

> Connection before control. Truth before belief. Repair before rebuild.
