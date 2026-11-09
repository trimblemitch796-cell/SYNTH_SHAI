# SYNTH_SHAI × Spatial Guards — content-bound worker research (V0.1)

**Status:** offline research only; **144 HOLD remains**. No deployment, no live action, no independent security review.

**Base main revision:** `f3f219769634efc485b87ac1fbd027ef326201f9`  
**Branch:** `research/content-bound-worker-v01`

## Change scope

- `research_content_binding_v01.py`: strictly bounded, explicitly declared nested Base64 / percent decoding (up to 3 layers), UTF-8 validation, SHA-256 digest of canonical decoded text and a **synthetic example** deny marker. Unknown, malformed, ambiguous or over-deep encodings HOLD. This is a prototype policy, not a DLP solution.
- `offline_worker_v3.py`: requires an exact new JSON envelope `{request,approval,content}`. Content is `{raw_b64,encodings}`, with canonical Base64 as the transport encoding and encodings declared outermost to innermost. The worker validates content before handing off to existing signed, single-use synthetic dispatch.
- `test_worker_content_binding_v01.py`: direct child-worker and V4.1 parent-path regression tests. Existing worker, resource-limit and parent-lifecycle fixtures are updated for the strict envelope.
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

The 25-case `test_research_content_binding_v01.py` suite is available in the associated local research package; do **not** claim those 25 are part of GitHub CI until the suite is committed. The GitHub branch contains the new 20-case integration suite. CI must be checked separately on the branch head before claiming a repository pass.

## Known limitations and test gates

1. `offline_dispatch_v3.dispatch_simulation` is still a separately importable in-process function. The new *worker entrypoint* prevents direct bypass **only for requests routed through that worker**; it does not impose a system-wide in-process gate or trusted OS isolation.
2. Encoding detection is a bounded heuristic: legitimate Base64-looking text may HOLD, while unrecognized encodings and transformed Unicode may evade this example marker. No claim of complete sensitive-content detection.
3. The signed digest binds the **final decoded text**, not the raw outer transport representation or encoding declaration. This is appropriate only to this explicitly designed prototype policy; alternate representations and Unicode normalization require further review.
4. The local SQLite replay store, configured keys, clock and worker process are trusted assumptions. Resource limits do not isolate filesystem, network, credentials or descendant processes.
5. Comprehensive regression, CI checks, concurrency, performance measurements and independent adversarial security review remain separate requirements.

**Approval contract:** a simulated success never authorizes real action. No worker, network capability, external integration or deployable service is being enabled. `144 HOLD` remains default for consequential use.
