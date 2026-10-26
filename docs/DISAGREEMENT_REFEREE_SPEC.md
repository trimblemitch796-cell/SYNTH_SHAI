# Disagreement referee — design specification

**Status:** DESIGN SPEC ONLY, NOT IMPLEMENTED, NOT INDEPENDENTLY REVIEWED. Owner design review 27 October 2026: no code changed or deployed.  
**Scope:** SYNTH_SHAI offline research prototype. No live deployment authorisation.  
**Prepared:** 27 October 2026, against `main` at `406440d`. An implementation must record the exact commit it was built and reviewed on.

## Purpose and principle

When several AI models answer the same item (for example a future WhatsApp `/all` command), they will sometimes disagree. This spec defines how SYNTH_SHAI handles that **without guessing and without taking sides**.

**Principle: the supervisor (MANIAC) never becomes the deciding vote.** It only referees: it applies a deterministic check fixed in advance, and it routes the result. It may not add its own opinion, a confidence score, a preference for one model, or a majority count to break a tie. If no check can decide, a human decides.

**Passing the same check does not prove claims agree.** A check may be too weak to tell two different answers apart, so agreement is decided only by the cosmetic-normalisation rule (section 2), never by "both passed".

## 1. Supervisor verdict (default output)

By default SYNTH_SHAI sends **one** message per item:

- **Synthesized verdict:** the claim shared by the winning models (section 3). If the item is on `144 HOLD` for any reason (sections 3–5), the verdict says `144 HOLD — awaiting human review` and nothing else is asserted.
- **One-line disagreement note** whenever a disagreement flag was raised, e.g. `Models disagreed on the total (A: 412, B: 421); recomputation passed A only.`
- **Raw outputs** are *not* sent by default. If they pass the synthetic-data gate (section 5) they are written to `999000 AUDIT` and can be viewed on request by item ID; otherwise only their hash is kept.

The verdict never claims approval: `approval_granted` stays False, as everywhere else in SYNTH_SHAI.

## 2. Usable answers and the disagreement flag

**Usable answer:** a non-empty answer returned within its timeout and without error. A timed-out, errored or empty answer is `no_answer`: it is **never** counted as agreement and **never** as a loss.

**Fewer than two usable answers:** there is nothing to triangulate, so the item goes to `144 HOLD` (reason `insufficient_answers`), **even if the single answer would pass the check**. There is no single-answer shortcut.

With two or more usable answers, a flag is raised wherever answers differ **materially**:

| Kind | Definition | Examples | Action |
| --- | --- | --- | --- |
| **Material** | The answers would lead to a different fact, number, decision, action or code behaviour | Different totals; "safe" vs "unsafe"; a different function result | Raise the flag and route to `555000 TRIANGULATE` |
| **Cosmetic** | The same claim after the **documented normalisation**: whitespace, case, ordering of unordered items, exact unit conversion, rounding within a tolerance fixed in advance | `4.0` vs `4`; the same list in a different order | No flag. Record `cosmetic_diff=true` in the audit only |

If it is unclear whether a difference is material, treat it as **material** (fail closed). The same normalisation decides "equivalent" everywhere in this spec.

**Flag fields:** `flag_id` (SYNTHETIC-), `item_id`, `item_sha256`, `models` (name + version each), `claims` (a short normalised claim per model), `difference` (one line), `kind` (`material`), `raised_at`, `route` (`555000 TRIANGULATE`).

**Routing:** `555000 TRIANGULATE` treats each model as a source. Models can share training data and errors, so agreement among them is **not** independent evidence. TRIANGULATE never resolves a flag by counting; it hands it to the referee.

## 3. Deterministic third check (the referee)

The referee is a check with **no opinion of its own**. It is:

- **Fixed in advance:** chosen per item type and registered before the models answer (check ID + version + hash of the check code or data).
- **Reproducible offline:** the same inputs give the same result on any machine, with no network and no model calls. A check must pass a determinism self-test (the same input run twice) before use.
- **Mechanical:** for example a unit test, a schema or type check, a SHA-256 or known-answer comparison, an exact recomputation, or a lookup in a pinned reference table.

The check returns **pass or fail per usable answer**. The referee outcome is then exactly one of:

| Outcome | Rule | Result |
| --- | --- | --- |
| `MATCH` | At least one model passes **and** all passing claims are equivalent after normalisation | Winner = the set of passing models; losers = the failing models, each logged with the check's failure reason |
| `CHECK_INSUFFICIENT` | Two or more models pass with **materially different** claims | The check is too weak to tell them apart: `144 HOLD`, then `444000` |
| `NO_MATCH` | No model passes | `144 HOLD`, then `444000` |
| `NO_CHECK` | No registered check exists for this item type, **or** the check is unstable (reason `check_unstable`) | `144 HOLD`, then `444000` |

The check's output is recorded verbatim. MANIAC applies it; it never edits it or interprets around it.

## 4. Routing to a human

`NO_MATCH`, `NO_CHECK`, `CHECK_INSUFFICIENT`, `insufficient_answers` and `privacy_rejected` all send the item to **`144 HOLD`**, then **`444000 VERIFY / HUMAN APPROVAL`**. The human sees the claims (or their hashes, if redacted), the difference and the check result, and records a decision through the existing human-decision path, which requires an `operator_id`.

Never guess. Never majority-vote. Never pick the "more confident" or "usually better" model. Until a human decides, the item stays on HOLD.

## 5. Disagreement log and privacy rule

An append-only record per flag, kept separately from but linked to `999000 AUDIT`. Its purpose is **training and evaluation data**: detecting model drift over time and building held-out test cases.

| Field | Content |
| --- | --- |
| `id` | `SYNTHETIC-` prefixed ID |
| `timestamp` | When the flag was raised (and when it was resolved) |
| `item_sha256` | Hash of the prompt/item |
| `models` | Name and version of every model involved, with `no_answer` where applicable |
| `claims` | A short normalised claim per model, or `REDACTED` (see below) |
| `check` | Check ID, version and code/data hash, or `none` |
| `outcome` | `MATCH`, `CHECK_INSUFFICIENT`, `NO_MATCH` or `NO_CHECK`, or `HOLD` with reason `insufficient_answers` / `privacy_rejected` |
| `winners` / `losers` | Model sets, or `none` |
| `reason` | The check's failure reason for each loser, or why the item went to a human |
| `human_decision` | `operator_id`, decision and reason if a human decided; otherwise `none` |
| `audit_ref` | Hash of the linked `999000 AUDIT` entry |

**Privacy rule (synthetic-data gate), reject-by-default:**

- Before anything is written to `999000 AUDIT` or this log, every prompt and output passes a **synthetic-data gate**. The prototype accepts only `SYNTHETIC-` IDs and synthetic content.
- If a prompt or output fails the gate (it looks like real personal data), its raw text is **not stored**. The record keeps only its SHA-256 hash, its length and `REDACTED: <reason>`, and the item goes to `144 HOLD` (reason `privacy_rejected`).
- This is rejection, not best-effort scrubbing: nothing is "cleaned" and then kept.
- **Limit:** the gate is heuristic, so it can miss real data or wrongly reject synthetic data. Avoid real data at the source. See [THREAT_MODEL.md](THREAT_MODEL.md).

**Tamper limits:** the same as the existing audit. It is a local file with a hash chain and anchor; same-user or root access can still rewrite it, and a full rewrite is undetectable without an external anchor (see THREAT_MODEL.md).

## Mapping to existing gate codes

| Gate | Role in this spec |
| --- | --- |
| `555000 TRIANGULATE` | Receives the flag; needs two or more usable answers; treats models as sources; never resolves by counting |
| Referee (inside TRIANGULATE) | Per-model pass/fail, giving `MATCH` / `CHECK_INSUFFICIENT` / `NO_MATCH` / `NO_CHECK` |
| `144 HOLD` | Entered on `CHECK_INSUFFICIENT`, `NO_MATCH`, `NO_CHECK` (including `check_unstable`), `insufficient_answers`, `privacy_rejected`, or any internal error |
| `444000 VERIFY / HUMAN APPROVAL` | A human resolves held items; a `MATCH` result still goes through normal VERIFY before any action |
| `999000 AUDIT` | Stores (synthetic-gated) raw outputs, the flag, the check result and the decision |
| `111000 COMPARE / LEARN` | Reads the disagreement log for per-model win/loss, `no_answer` and check-failure rates over time (drift) |
| `Δ BALANCE` | BALANCED only if every gate completed and the audit verifies. An unresolved flag or HOLD means UNBALANCED |

The open question of whether a clean human **REJECTED** should count as BALANCED is **unchanged and still deferred to the independent reviewer**.

## Edge cases

| Case | Handling |
| --- | --- |
| All passing models give equivalent claims | `MATCH`; winners = all passing models |
| Several models pass with materially different claims | `CHECK_INSUFFICIENT` → HOLD. Passing the same check is not agreement |
| Two of three pass and agree, one fails | `MATCH`; the failing model loses with its reason. This is a check result, not a vote |
| Check is flaky (different results on re-run) or errors | `NO_CHECK`, reason `check_unstable` → HOLD |
| A model times out, errors or answers empty | `no_answer`: neither agreement nor loss. If fewer than two usable answers remain → HOLD (`insufficient_answers`) |
| The same model gives two different answers on re-run | An internal disagreement: both claims are logged under that model and refereed the same way; it counts as instability for drift tracking |
| Prompt or output looks like real personal data | Hash + length + `REDACTED` only → HOLD (`privacy_rejected`) |
| Check passes but the item is unsafe | The referee only settles the factual dispute; all other gates (ethics, consent, evidence, VERIFY) still apply |

## Non-goals and limits

- **Not implemented.** No code exists for this yet; this document is a design spec.
- **Offline research prototype.** No live messaging, model API calls or deployment are authorised by this spec.
- **Not a medical device or a safety certification.** Referee results are not clinical, legal or safety sign-off.
- **Model agreement is not truth,** and neither is passing a weak check. Only an adequate check or a human resolves a dispute.
- **Approval records don't authenticate a human.** `operator_id` is caller-supplied text (see THREAT_MODEL.md); signed approvals are on the roadmap, not done.
- **The privacy gate is heuristic,** and the same-process and local-file limits from THREAT_MODEL.md apply unchanged.

## Acceptance criteria for a future implementation (test ideas)

1. Two models give materially different numbers and a recomputation passes exactly one: `MATCH`, the loser is logged with the reason, and the verdict has a one-line note.
2. Several passing models with equivalent claims (after normalisation): `MATCH`, and winners = all passing models.
3. Several passing models with materially different claims: `CHECK_INSUFFICIENT` → `144 HOLD` → `444000`, with no verdict asserted.
4. Cosmetic-only differences raise no flag.
5. `NO_MATCH` and `NO_CHECK` both give `144 HOLD` → `444000`.
6. There is no code path where MANIAC breaks a tie by count, confidence or preference: 2-vs-1 models with no check must HOLD.
7. A flaky check (patched to alternate results) gives `NO_CHECK` with `check_unstable` → HOLD.
8. One model times out and only one usable answer remains: `144 HOLD` (`insufficient_answers`), even when that answer passes the check. A timeout is never agreement or a loss.
9. Same model, two answers: it is flagged and refereed.
10. Privacy reject: a non-synthetic-looking prompt or output stores only its hash, length and `REDACTED` marker (no raw text anywhere in the audit or log), and the item goes to `144 HOLD` (`privacy_rejected`).
11. Every log record has all fields and a `SYNTHETIC-` ID; the log is append-only and verifies like the audit chain.
12. `approval_granted` is always False; a `MATCH` still requires normal VERIFY before any action; the same inputs and check give the same outcome and gate path.

## Resolved review points (27 Oct 2026)

From Mitch's design review (docs only; no code changed or deployed):

1. **MATCH contradiction:** the check is now pass/fail per model. `MATCH` = at least one passer and all passers equivalent; winners are the passing set. The new outcome `CHECK_INSUFFICIENT` covers passers that differ.
2. **Timeout contradiction:** there is one rule. A timeout, error or empty answer is `no_answer`, and fewer than two usable answers means `144 HOLD` (`insufficient_answers`). The single-answer shortcut is removed.
3. **Privacy contradiction:** an explicit reject-by-default synthetic-data gate now runs before the audit or log. Failures store only the hash, length and `REDACTED` marker, then `144 HOLD` (`privacy_rejected`).
4. **Weak checks:** added the principle that passing the same check does not prove claims agree.
