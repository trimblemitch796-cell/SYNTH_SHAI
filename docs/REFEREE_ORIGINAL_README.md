# SYNTH_SHAI disagreement referee — offline V0.1

Built 27 October 2026 from the supplied design specification. This is a working,
bounded numeric implementation, not full implementation of the broader spec.
Not connected to GitHub, WhatsApp, model APIs, or the existing SYNTH_SHAI gates.
No live deployment, independent review, safety certification, or approval authority.

## Run (Python 3.10+, standard library only)

```sh
python3 referee.py
python3 -m unittest -v
```

Demo: two synthetic answers, 412 and 421, for 200 + 212. The checked result is
412; the message explicitly requires VERIFY and grants no approval.

## API

1. Create `Plan(item_id, operands)` before obtaining model responses.
2. Save `plan.commitment` in the caller's trusted state before collecting answers.
3. Create a tuple of `Answer(model_alias, version_alias, attempt_id, raw)` records.
   IDs must be SYNTHETIC- followed by digits. `None` means no answer.
4. Use `Journal(path).record(plan, answers, saved_commitment)` for audited use.
   `evaluate` is pure evaluation only; do not treat it as audited completion.
5. Use `message(result)` for the default output. `Journal.read(item_id)` retrieves
   the accepted raw numeric outputs. Protect that access in the integrating app.
6. Preserve each returned `audit_anchor` outside the writable database if you
   need truncation/full-rewrite detection. `verify(expected_anchor)` checks it.

This module returns routing labels only. It does not implement downstream gates,
operator authentication, human decisions, permission restoration, or action execution.
Every result has `approval_granted=False`. A MATCH is not BALANCED or permission.

## Resolved design ambiguities

- MATCH means at least one response equals the single exact recomputed total.
  Multiple passing responses are allowed; majority and confidence have no role.
- Fewer than two nonmissing answers always HOLD. Two remaining answers can be
  checked even when another provider has no answer.
- All agreement is checked too; identical wrong answers produce NO_MATCH.
- Missing check, check exceptions, instability, and audit failures HOLD.
- No arbitrary plugin checks or submitted code are executed. The built-in exact
  sum verifier completely settles the supported claim. General schema/test
  checks that allow incompatible claims are deliberately not supported.
- Privacy: this build accepts only bounded decimal strings and synthetic numeric
  aliases, not prose. Use synthetic fixtures ONLY. Numeric identifiers can still
  be personal data: validation is NOT a personal-data detector. Raw accepted
  numeric answers are stored locally; rejected free text is not logged.
- Units, fuzzy wording, unordered lists, tolerances, free-text synthesis, provider
  name/version mappings, drift dashboards, and human-resolution workflows are
  future integration work. Same-model reruns retain distinct attempt IDs.

## Audit and trust limits

SQLite transactions serialize concurrent appends. Audit and disagreement records
are written atomically into separate tables linked by the audit hash. The public
API offers append/read/verify; database owners can still edit or delete anything.
No signatures, encryption, access control, external anchoring service, or sandbox
is provided. A full rewrite cannot be detected without a trusted external anchor.
Item IDs cannot be replayed into the same journal. Invalid input is returned as
HOLD without persisting unvalidated content; caller error telemetry is separate.

The immutable plan and source hash bind the supplied check and inputs. They do
not prove WHEN registration occurred: the trusted caller must capture the
commitment before responses arrive. The same-process caller can monkey-patch code.
Checking twice catches the tested alternating result, not every nondeterministic
failure; cross-machine reproducibility is not established by this local test run.
The built-in check uses bounded exact rational arithmetic and no network or eval.

## Evidence and provenance

25 local unit tests passed, including minority-correct, incorrect agreement,
missing answers, injected unstable/erroring check, replay, concurrent writes,
tampering, external-anchor truncation detection, and storage failure. These are
self-authored local tests, not independent verification or repository CI results.
See TEST_RESULTS.txt and SHA256SUMS.txt for this delivered build. The original
spec cites repository commit 406440d; this standalone build was not checked out
from or tested against that commit. Record the actual repository commit when
integrating and have the integration reviewed separately.

ORIGINAL_SPEC.md is preserved unchanged for comparison; the decisions and scope
above describe what the implementation actually supports.
