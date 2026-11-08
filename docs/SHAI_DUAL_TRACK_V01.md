# SHAI dual-track evidence-to-synthetic-review V0.1

**Status:** offline research demonstration only. Not a ChatGPT installation, autonomous agent, authenticated hosted service, or authorisation to act. **144 HOLD for all consequential actions.**

## Why this exists

SHAI's conversational/research path and signed local review path existed as distinct prototypes. This change adds a bounded composition in shai_dual_track_v01.py and negative tests in test_shai_dual_track_v01.py to check the trust boundary from evidence intake to a **fixed synthetic-only** review.

User-defined symbolic sequence, with no cryptographic or operating-system authority:

- 111000 LEARN: examine source and failing tests.
- 222000 RE-OBSERVE: check the exact commit and present limits.
- 333000 DEFINE: accept only the synthetic_review action type.
- 555000 TRIANGULATE: require appropriately shaped evidence references and a separate trusted signed approval.
- 444000 HUMAN AUTHORITY: a symbol is never an authenticated credential, signature, release permit, or command to deploy.

## Actual implemented path

1. plugins/shai_mcp_v01/core.py **only validates syntax** of the claim, SHA and GitHub Actions run URL. It does NOT fetch GitHub, authenticate provenance, fact-check a claim or grant permission.
2. If a claim/reference is invalid, the wrapper immediately returns 144 HOLD and does **not** consume the approval.
3. If references have the expected shape, the wrapper passes the request and approval to offline_dispatch_v3.dispatch_simulation.
4. That **existing** dispatcher only accepts action synthetic_review and calls an existing strict policy and Ed25519 single-use approval check with host-provided keys, trusted database path and time.
5. The successful output is **SIMULATED_REVIEW_ONLY**, with only the fixed synthetic marker synthetic_review_recorded. It performs no GitHub issue creation, web/API request, message sending, deployment, device access or execution.
6. Its output ALWAYS explicitly retains consequential_action_state = 144 HOLD and external_action_performed = False.

No new network capability, tool endpoint, operator authentication service, trusted host, OS sandbox, web account or robot/finance/medical action was added. This is **in-process Python**; the caller could bypass it, and the surrounding host remains a trusted assumption.

## Verification

Run project-maintained tests on the exact candidate commit:

    python -m unittest test_shai_dual_track_v01 -v
    python -m unittest discover -v

The 11 new tests cover successful simulated-only review, missing approval, replay, invalid evidence and claim, exact plan binding, untrusted key, expiry, prohibited deployment, injected callback and unsafe replay store. The tests use a generated test-only Ed25519 key and a temporary SQLite file. No account credentials or real data.

**A passing test is not evidence of production authorization.**

## Gate for future online/reversible actions

Do NOT substitute these synthetic checks for a trusted execution controller. Before any real GitHub write or other external action, there must be a separately reviewed authenticated user identity, approval over the exact request and effect, least-privileged capability-owning service, strict allowlist, protected replay and revocation state, bounded network and filesystem permissions, audit and cancellation, third-party red-team/technical review, and explicit owner authorization. See issue #73 and independent review #21.

The existing read-only MCP adapter remains unchanged. The Android prototype remains unchanged.

**Conclusion:** offline evidence that conversational research intake can be followed by an approved *synthetic* review without claiming real action rights. 144 HOLD remains.
