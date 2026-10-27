# Disagreement referee — design specification

**Status:** DESIGN SPEC ONLY, NOT IMPLEMENTED, NOT INDEPENDENTLY REVIEWED.  
**Scope:** SYNTH_SHAI offline research prototype. No live deployment authorisation.  
**Prepared:** 27 October 2026, against `main` at `406440d`. An implementation must record the exact commit it was built and reviewed on.

## Purpose and principle

When several AI models answer the same item (for example a future WhatsApp `/all` command), they will sometimes disagree. This spec defines how SYNTH_SHAI handles that **without guessing and without taking sides**.

**Principle: the supervisor (MANIAC) never becomes the deciding vote.** It only referees: it applies a deterministic check fixed in advance, and it routes the result. It may not add its own opinion, a confidence score, a preference for one model, or a majority count to break a tie. If no check can decide, a human decides.

## 1. Supervisor verdict (default output)

By default SYNTH_SHAI sends **one** message per item:

- **Synthesized verdict:** the answer supported by the models that agree, or by the model that matched the deterministic check (section 3). If it was routed to a human (section 4), the verdict says `144 HOLD — awaiting human review` and nothing else is asserted.
- **One-line disagreement note** whenever a disagreement flag was raised, e.g. `Models disagreed on the total (A: 412, B: 421); recomputation matched A.`
- **Raw outputs** from every model are *not* sent by default. They are written to the audit log (`999000 AUDIT`) and the disagreement log (section 5), and can be viewed on request by referencing the item ID.

The verdict never claims approval: `approval_granted` stays False, as everywhere else in SYNTH_SHAI.

## 2. Disagreement flag

A flag is raised for every item where two or more model answers differ **materially**.

| Kind | Definition | Examples | Action |
| --- | --- | --- | --- |
| **Material** | The answers would lead to a different fact, number, decision, action or code behaviour. | Different totals; "safe" vs "unsafe"; a different function result; a missing required step | Raise the flag and route to `555000 TRIANGULATE` |
| **Cosmetic** | The same claim after normalisation: whitespace, case, ordering of unordered items, wording, units converted exactly, rounding within a tolerance set in advance | "4.0" vs "4"; same list in a different order | No flag. Record `cosmetic_diff=true` in the audit only |

If it is unclear whether a difference is material, treat it as **material** (fail closed).

**Flag fields:** `flag_id` (SYNTHETIC-), `item_id`, `item_sha256`, `models` (name + version each), `claims` (a short normalised claim per model), `difference` (one line), `kind` (`material`), `raised_at` (timestamp), `route` (`555000 TRIANGULATE`).

**Routing:** the flag goes through `555000 TRIANGULATE`, which treats each model as a source. Agreement among models is **not** independent evidence, because models can share training data and errors. So TRIANGULATE never resolves the flag by counting; it hands it to the referee.

## 3. Deterministic third check (the referee)

The referee is a check with **no opinion of its own**. It is:

- **Fixed in advance:** chosen per item type and registered before the models answer (check ID + version + hash of the check code or data).
- **Reproducible offline:** the same inputs give the same result on any machine, with no network and no model calls.
- **Mechanical:** for example a unit test, a schema or type check, a SHA-256 or known-answer comparison, an exact recomputation (arithmetic, a sort, a parser), or a lookup against a pinned reference table.

**Outcomes** (exactly one):

| Outcome | Meaning | Result |
| --- | --- | --- |
| `MATCH` | Exactly one model's claim passes the check | That model wins. Each loser is logged with the check's failure reason |
| `NO_MATCH` | No model's claim passes | Route to human (section 4) |
| `NO_CHECK` | No registered deterministic check exists for this item type | Route to human (section 4) |

The check's output is recorded verbatim. MANIAC applies it; it never edits it or interprets around it.

## 4. Neither matches, or no check exists

`NO_MATCH` or `NO_CHECK` sends the item to **`144 HOLD`**, then **`444000 VERIFY / HUMAN APPROVAL`**. The human sees the claims, the difference and the check result (if any), and records a decision through the existing human-decision path, which requires an `operator_id`.

Never guess. Never majority-vote. Never pick the "more confident" or "usually better" model. Until a human decides, the item stays on HOLD.

## 5. Disagreement log

An append-only record per flag, kept separately from but linked to `999000 AUDIT`. Its purpose is **training and evaluation data**: detecting model drift over time (one model starting to lose more often, a check type failing more often) and building held-out test cases.

| Field | Content |
| --- | --- |
| `id` | `SYNTHETIC-` prefixed ID |
| `timestamp` | When the flag was raised (and when it was resolved) |
| `item_sha256` | Hash of the prompt/item, not the text itself |
| `models` | Name and version of every model involved |
| `claims` | A short normalised claim summary per model |
| `check` | Check ID, version and code/data hash, or `none` |
| `outcome` | `MATCH`, `NO_MATCH` or `NO_CHECK` |
| `winner` / `losers` | Model(s), or `none` |
| `reason` | The check's failure reason for each loser, or why it went to a human |
| `human_decision` | `operator_id`, decision and reason, if a human decided; otherwise `none` |
| `audit_ref` | Hash of the linked `999000 AUDIT` entry |

**Data rules:** `SYNTHETIC-` IDs only, no personal data, and no raw prompts containing personal data (store hashes). **Tamper limits:** same as the existing audit. It is a local file with a hash chain and anchor; same-user or root access can still rewrite it, and a full rewrite is undetectable without an external anchor. See [THREAT_MODEL.md](THREAT_MODEL.md).

## Mapping to existing gate codes

| Gate | Role in this spec |
| --- | --- |
| `555000 TRIANGULATE` | Receives the disagreement flag; treats models as sources; never resolves by counting |
| Referee (inside TRIANGULATE) | Applies the deterministic check: `MATCH` / `NO_MATCH` / `NO_CHECK` |
| `144 HOLD` | Entered on `NO_MATCH`, `NO_CHECK`, a flaky check, a timeout that leaves fewer than two answers, or any internal error |
| `444000 VERIFY / HUMAN APPROVAL` | A human resolves held disagreements; a `MATCH` result still goes through normal VERIFY before any action |
| `999000 AUDIT` | Stores raw outputs, the flag, the check result and the decision |
| `111000 COMPARE / LEARN` | Reads the disagreement log to track per-model win/loss and check-failure rates over time (drift) |
| `Δ BALANCE` | The loop is BALANCED only if every gate completed and the audit verifies. An unresolved flag means UNBALANCED / HOLD |

The open question of whether a clean human **REJECTED** should count as BALANCED is **unchanged and still deferred to the independent reviewer**. This spec's outcomes are MATCH / NO_MATCH / NO_CHECK only.

## Edge cases

| Case | Handling |
| --- | --- |
| Both (all) models match the check | No material disagreement after the check: verdict = the shared claim. Log as `MATCH` with `winner=all`, and note that the original difference was not decisive under this check |
| Two of three match | The matching models win and the third loses. This is a check result, not a vote |
| Check is flaky (different results on re-run, or it errors) | Treat as `NO_CHECK`, route to HOLD and log `check_unstable`. A check must pass a determinism self-test (same input run twice) before use |
| A model times out or errors | Record as `no_answer`. If fewer than two answers remain there is no disagreement to referee: a single answer still goes through normal gates. Never treat silence as agreement |
| The same model gives two different answers (re-run) | Treat as an internal disagreement: log both claims under the same model, referee them the same way, and count it as instability for drift tracking |
| Check passes but the item is unsafe | The referee only settles the factual dispute; all other gates (ethics, consent, evidence, VERIFY) still apply |

## Non-goals and limits

- **Not implemented.** No code exists for this yet; this document is a design spec.
- **Offline research prototype.** No live messaging, model API calls or deployment are authorised by this spec.
- **Not a medical device or a safety certification.** Referee results are not clinical, legal or safety sign-off.
- **Model agreement is not truth.** Agreeing models can share the same error; only the deterministic check or a human resolves a dispute.
- **Approval records don't authenticate a human.** `operator_id` is caller-supplied text (see THREAT_MODEL.md); signed approvals are on the roadmap, not done.
- **Same-process and local-file limits** from THREAT_MODEL.md apply unchanged.

## Acceptance criteria for a future implementation (test ideas)

1. Two models give materially different numbers and a recomputation check exists: the matching model wins, the loser is logged with the reason, and the verdict has a one-line note.
2. Cosmetic-only differences (whitespace, order, `4.0` vs `4`) raise no flag.
3. `NO_MATCH` and `NO_CHECK` both give `144 HOLD` → `444000`, with no verdict asserted.
4. There is no code path where MANIAC breaks a tie by count, confidence or preference: a test with 2-vs-1 models and no check must HOLD.
5. A flaky check (patched to alternate results) gives HOLD with `check_unstable`.
6. A timeout or missing answer is never counted as agreement.
7. Same model, two answers: it is flagged and refereed.
8. Every disagreement log record has all fields and a `SYNTHETIC-` ID, and contains no raw personal text; the log is append-only and verifies like the audit chain.
9. Raw outputs are absent from the default message but retrievable from the audit by item ID.
10. `approval_granted` is always False, and a `MATCH` still requires normal VERIFY before any action.
11. Deterministic: the same inputs and the same check give the same verdict, log fields (except timestamps) and gate path.
