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
- PR #13: supervisor numeric-input and recovery-ID hardening **proposed in draft**; **not merged** at this review.

## Current PR #13
- Branch: `hardening/maniac-ushai-v31-gates`
- Changes: reject non-finite sensor values, bounds, limits, heartbeats and clocks; reject malformed request IDs; add nine adversarial regression-test methods.
- Status: source/tests present on branch. **Passing CI for this head commit has not been independently confirmed**. Do not merge until checks and review are completed.

## Outstanding release gates (144 HOLD)
- [ ] Run the full `python -m unittest discover -v` test suite on PR #13 and record the exact commit + results.
- [ ] Assess concurrency, duplicate requests, replay and SQLite persistence across restarts.
- [ ] Verify MANIAC + USHAI + V3.1 evidence-bridge integration with adversarial synthetic scenarios.
- [ ] Review trust-key provisioning, source independence and approval/consent provenance.
- [ ] Review public repo and git history for secrets, private data and licensing.
- [ ] Obtain independent security and hazard review before consequential applications.

## Mandatory boundaries
- `144 HOLD` for faults, missing or contradictory evidence, replay, and unauthorized requests.
- `444000` is verification and human review **not deployment authorization**.
- No network operations, external account access, money movement, physical actuation or autonomous authority granted by these prototypes.
- Human choices and approved scope remain external to test-result validity.

> Connection before control. Truth before belief. Repair before rebuild.
