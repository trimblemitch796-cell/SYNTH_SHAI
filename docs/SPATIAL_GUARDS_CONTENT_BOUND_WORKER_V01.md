# SYNTH_SHAI × Spatial Guards — content-bound worker research (V0.1)

**Status:** offline research only; **144 HOLD remains**. No deployment, no live action, no independent security review.

**Base main revision:** `f3f219769634efc485b87ac1fbd027ef326201f9`  
**Branch:** `research/content-bound-worker-v01`

## Change scope

- `research_content_binding_v01.py`: strictly bounded, explicitly declared nested Base64 / percent decoding (up to 3 layers), UTF-8 validation, SHA-256 digest of canonical decoded text and a **synthetic example** deny marker. Unknown, malformed, ambiguous or over-deep encodings HOLD. This is a prototype policy, not a DLP solution.
- `offline_worker_v3.py`: requires an exact new JSON envelope `{request,approval,content}`. Content is `{raw_b64,encodings}`, with canonical Base64 as the transport encoding and encodings declared outermost to innermost. The worker validates content before handing off to existing signed, single-use synthetic dispatch.
- `test_worker_content_binding_v01.py`: 29 direct child-worker and V4.1 parent-path test methods at this revision (24 from the verified baseline plus five new adversarial/contract tests). Four additional tests were added earlier to `test_v41_offline_boundary.py`. Existing worker, resource-limit and parent-lifecycle fixtures use the strict envelope.
- **Backward incompatible by design**: the old `{request,approval}` envelope now returns `144 HOLD` rather than bypassing decoded-content checks. No migration bypass switch is provided.

## Example envelope schema

```json
{
  "request": {"request_id": "test-only", "action": "synthetic_review", "plan_sha256": "<64 lower-case hex characters of SHA-256 of canonical UTF-8 plaintext>"},
  "approval": {"operator_id": "test-only", "request_id": "test-only", "action": "synthetic_review", "plan_sha256": "<same hash>", "nonce": "<unique nonce>", "expires_at": 100030, "signature": "<test-only Ed25519 signature>"},
  "content": {"raw_b64": "<canonical Base64 transport of raw text bytes>", "encodings": ["base64"]}
}
```

`raw_b64` represents the raw user-supplied bytes. `encodings` represent the *nested user content* encodings, not the outer transport Base64. A trusted test harness must sign the exact canonical digest, with test-only keys, a trusted clock and a trusted SQLite replay store.

## Local test evidence

Before pushing this branch, tested copies of the revised worker and adapter ran successfully in a Linux local environment (Python 3.13.5, cryptography 46.0.4):

```sh
python -m unittest test_worker_content_binding_v01 test_research_content_binding_v01 -q
# Ran 45 tests in 17.873s — OK
```

The 25-case `test_research_content_binding_v01.py` suite was local-only and is **not part of GitHub CI**; the 45-test figure above is *historical*, from before the later V4.1 fixtures and Unicode additions. The tracked integration module grew from 20 to 24 tests by verified head `6e9765dd`, and now to **29** tests (five further research cases). These counts are module-specific, not whole-repository CI totals.

**Verified prior head:** GitHub Actions at `6e9765dd2339aed03995b998d1cee77d1e7ca158` reported **742/742 tests** on both Python 3.11 and 3.13; V3.1 CATHARSIS, dependency-advisories and reachable-history-secrets also passed. **This follow-up revision is not considered CI-verified until GitHub completes its fresh jobs.**

## Known limitations and test gates

1. `offline_dispatch_v3.dispatch_simulation` is still a separately importable in-process function. The new *worker entrypoint* prevents direct bypass **only for requests routed through that worker**; it does not impose a system-wide in-process gate or trusted OS isolation.
2. Encoding detection is a bounded heuristic: legitimate Base64-looking text may HOLD, while unrecognized encodings and transformed Unicode may evade this example marker. The scan additionally NFKC/NFKD-folds and ignores combining marks (including variation selectors) **only in its non-authoritative marker comparison**; the signed UTF-8 bytes remain unchanged. This can create false positives; it is not actual DLP, Unicode confusable coverage, or complete sensitive-content detection.
3. The signed digest binds the **final decoded text**, not the raw outer transport representation or encoding declaration. This is appropriate only to this explicitly designed prototype policy; alternate representations and Unicode normalization require further review.
4. The local SQLite replay store, configured keys, clock and worker process are trusted assumptions. Resource limits do not isolate filesystem, network, credentials or descendant processes.
5. Comprehensive regression, CI checks, concurrency, performance measurements and independent adversarial security review remain separate requirements.

**Approval contract:** a simulated success never authorizes real action. No worker, network capability, external integration or deployable service is being enabled. `144 HOLD` remains default for consequential use.


## 10 November 2026 CI investigation

PR #112 initial pull-request workflows (`verification`, `V3.1 CATHARSIS`,
`release security`) returned an `Internal server error` annotation and
did not expose actionable failing-test logs. The dependency-advisories job
reported success. GitHub API attempts to retry those three runs returned
`403 This workflow run cannot be retried`.

This documentation-only commit requests a fresh push-triggered and PR-triggered
CI evaluation of the existing experimental research implementation. No
authorization scope changes; `144 HOLD` remains in force.

Do not mark the PR green unless the new exact-revision checks complete.

## Five-case safe comparison scope (follow-up)

The added signed READ/WRITE/unknown-intent regressions are native SYNTH_SHAI tests; they do **not** run Spatial Guards or establish equivalent clinical state-machine behavior. Our worker intentionally has no real READ, WRITE, or human-review queue. A signed fixed synthetic review can only return `SIMULATED_REVIEW_ONLY`, not authorize tool execution. The new replay test shows that re-encoding the same canonical content cannot reuse a consumed approval.

No private third-party evaluation fixtures, code, benchmark payloads, or clinical data are published in this branch. Future cross-project comparison requires a separately approved, synthetic, common test contract and execution of both actual engines, with comparable outcomes and measured evidence. Keep this PR in draft under **144 HOLD**.
