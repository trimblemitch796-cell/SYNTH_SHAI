# SYNTH_SHAI V3.1 — Build Status
_Last reviewed: 25 October 2026 (Australia/Brisbane)_

## Scope
This is an **offline software-prototype** progress record, not a declaration that the entire SYNTH_SHAI vision, a physical MANIAC chip, or a public AI service is complete.

**Planning estimate: ~78% of the currently defined V3.1 prototype milestones** (subjective; not based on a weighted, independently validated requirements trace). The remaining 22% is **not** a measured development effort or time estimate.

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
- Step 7 (`shai-digital-twin` branch): SHAI digital twin + ELO-ECTRIC power model. Software only, illustrative numbers, **not hardware-ready**. Proposed, not merged at this review.

## Current test count
`python3 -m unittest discover -v`: **243 tests, all passing** (local run on `shai-digital-twin`, 25 October 2026).
`python3 -m maniac.simulation`: 33/33 scenarios pass.

## Next step
With step 6, every gate in Mitch's flow exists as offline code. Step 7 adds a simulated SHAI body and power model that can only move through the full loop plus a human approval. Suggested next work, for Mitch to decide: an independent outside review (see issue #21), persistent audit storage, wiring V25 TRI5 into `run_loop`, and deciding whether a clean human REJECTED counts as BALANCED.

## Outstanding release gates (144 HOLD)
- [~] Assess concurrency, duplicate requests, replay and SQLite persistence across restarts. Local single-database cases are tested in PR #19. Cross-device replay is not established.
- [x] Verify MANIAC + V3.1 evidence-bridge integration with adversarial synthetic scenarios (`python3 -m maniac.simulation`, 33 scenarios, including full-loop recovery and SHAI twin). USHAI is covered only by its fixed baseline input.
- [ ] Review trust-key provisioning, source independence and approval/consent provenance.
- [ ] Review public repo and git history for secrets, private data and licensing.
- [ ] Obtain independent security and hazard review before consequential applications.

## Mandatory boundaries
- `144 HOLD` for faults, missing or contradictory evidence, replay, and unauthorized requests.
- `444000` is verification and human review **not deployment authorization**.
- No network operations, external account access, money movement, physical actuation or autonomous authority granted by these prototypes.
- Human choices and approved scope remain external to test-result validity.

> Connection before control. Truth before belief. Repair before rebuild.
