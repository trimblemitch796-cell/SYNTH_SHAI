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
- MANIAC_SIMULATION (step 4): offline fault injector, proposed in the `maniac-simulation` PR; not merged at this review.

## Current test count
`python3 -m unittest discover -v` on branch `maniac-simulation`: **121 tests, all passing** (local run, 25 October 2026).

## Outstanding release gates (144 HOLD)
- [ ] Assess concurrency, duplicate requests, replay and SQLite persistence across restarts.
- [x] Verify MANIAC + V3.1 evidence-bridge integration with adversarial synthetic scenarios (`python3 -m maniac.simulation`, 19 scenarios). USHAI is covered only by its fixed baseline input.
- [ ] Review trust-key provisioning, source independence and approval/consent provenance.
- [ ] Review public repo and git history for secrets, private data and licensing.
- [ ] Obtain independent security and hazard review before consequential applications.

## Mandatory boundaries
- `144 HOLD` for faults, missing or contradictory evidence, replay, and unauthorized requests.
- `444000` is verification and human review **not deployment authorization**.
- No network operations, external account access, money movement, physical actuation or autonomous authority granted by these prototypes.
- Human choices and approved scope remain external to test-result validity.

> Connection before control. Truth before belief. Repair before rebuild.
