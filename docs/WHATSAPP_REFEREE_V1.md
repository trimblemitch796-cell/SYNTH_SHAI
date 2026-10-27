<!-- Written by ChatGPT (OpenAI) as the package README; adapted for this repo. -->
# SYNTH_SHAI — WhatsApp Bridge + Deterministic Referee (offline integration prototype)

**NOT LIVE / NOT DEPLOYED / NOT INDEPENDENTLY REVIEWED.** No real AI provider integration, no outbound WhatsApp messages, no human-authentication or approval implementation. No changes have been pushed to GitHub by this package.

This is a **self-contained, additive GitHub-ready folder** joining two uploaded prototypes. It preserves each implementation in separate directories and adds a small **offline synthetic-fixture integration seam**. Merged to main via PR #53; the repo README was not replaced.

## Layout

- `whatsapp/bridge.py`: inbound-only Meta webhook signature verification and human-review HOLD draft; no outbound API.
- `whatsapp/referee_adapter.py`: offline-only numeric referee demonstration, **not invoked by webhook**.
- `maniac/synth_shai_referee.py`: Mitch's SYNTH_SHAI Referee V0.1 with local spec fixes (insufficient_answers, privacy_rejected, HOLD labels/gates, check_unstable, replay_rejected). The package's original unfixed copy (`referee/`) was removed as a duplicate.
- `test_integration.py`: demonstrates a synthetic 412-vs-421 disagreement resolves to checked 412 while retaining approval gate and never sending a message.
- `docs/BRIDGE_ORIGINAL_README.md`, `docs/REFEREE_ORIGINAL_README.md`: original READMEs, retained for provenance. The package's spec copy was outdated (pre-PR #51) and was dropped; `docs/DISAGREEMENT_REFEREE_SPEC.md` is authoritative.
- CI: the package's `offline-tests.yml` workflow was dropped as redundant; the existing SHA-pinned `verification.yml` already runs `python -m unittest discover` (which includes `whatsapp/test_bridge.py` and `test_integration.py`) on every push and pull request.

## Test (Python 3.11+, no external packages)

```bash
python3 -m unittest discover -s . -p 'test*.py' -v
```

## Optional local webhook smoke test (inbound only)

```bash
export SHAI_VERIFY_TOKEN='YOUR_UNIQUE_SECRET'
export SHAI_META_APP_SECRET='YOUR_META_APP_SECRET'
python3 whatsapp/bridge.py
```

`127.0.0.1:8080` is the default bind. Never commit real secrets. Binding to `0.0.0.0` prints a warning. Do not publicly expose without secure HTTPS ingress, identity authentication and independent review.

## Exact safety boundary

- WhatsApp `/compare` **does not** automatically invoke the referee. There are no provider adapters or collected model answers.
- The offline referee accepts bounded synthetic numeric claims for an **exact sum** only, not general discussions, arbitrary claims or code execution.
- An integration must pre-register the referee plan + hash **before** collecting model answers. The supplied demonstration wrapper creates the plan immediately before evaluating already-present synthetic answers; it is strictly a fixture and **is not a compliant pre-registration workflow**.
- A referee `MATCH` determines a checked numeric result; it **does not authorise WhatsApp delivery, real-world action, or mark 444000 approval as granted**.
- The referee SQLite journal can be edited or rewritten by its owner; an independently protected audit anchor is required for stronger tamper evidence. Do not record personal data in synthetic test fixtures.
- Existing SYNTH_SHAI repository controls, threat model, human authority and external security review remain authoritative. This archive has **not** been checked against the current repository commit.

## GitHub PR recommendation

Branch: `feature/whatsapp-referee-offline-v1`
Title: `Add inbound-only WhatsApp bridge and offline numeric disagreement referee`

PR description: "Add two independent offline prototypes, a synthetic-only integration seam, tests and documentation. No auto-replies, provider API connectivity or action authority. Independent security review, webhook replay prevention, and authenticated review workflow remain open before deployment."

## Hardening (fix/whatsapp-bridge-hardening-20261027)

- **Persistent duplicate protection:** seen message ids are stored as SHA-256 hashes in SQLite (`SHAI_DEDUPE_DB`, default `.shai_data/whatsapp_seen_ids.sqlite`, gitignored), with a 24h TTL and a 10,000-row cap, and survive a restart. A duplicate returns 200 and creates no second HOLD. If the store errors, the webhook returns 503 so Meta retries (fail closed); the server refuses to start if the store is unusable.
- **Rate limiting:** sliding windows per sender (keyed by a hash of `from`, never the number itself) and globally: `SHAI_RATE_PER_SENDER` (default 10), `SHAI_RATE_GLOBAL` (default 100), `SHAI_RATE_WINDOW_SECONDS` (default 60). Over-limit messages are dropped and counted in the log, with no HOLD created, and still return **200**: Meta retries non-2xx responses, so a 429 would cause a retry storm.
- **Secrets:** the repo `.gitignore` now ignores `.env` and `.env.*` (but not `.env.example`) and `.shai_data/`.

## 144 HOLD review queue (feature/hold-review-queue-20261028)

Every new inbound text that passes the signature, dedupe and rate-limit checks is stored as a `PENDING_REVIEW` item in `whatsapp/review_queue.py`. The webhook still answers 200 straight away.

- **Storage:** SQLite at `SHAI_REVIEW_DB`, default `.shai_data/whatsapp_review.sqlite`, which is gitignored. The DB is **sensitive**: it keeps the message text, because a human has to read it. The sender number and the message id are stored only as SHA-256 hashes. If the store fails, the webhook un-marks the ids as seen and returns 503, so Meta's retry is accepted later.
- **Review endpoints** (same server):
  - `GET /review/items[?status=PENDING_REVIEW|APPROVED_NOT_SENT|REJECTED]`;
  - `GET /review/items/<HOLD-id>`;
  - `POST /review/items/<HOLD-id>/approve|reject` with JSON `{"reviewer": "...", "reason": "..."}` (reason required, max 500 characters);
  - `GET /review/audit`.
- **Auth, fail closed:**
  - `Authorization: Bearer <SHAI_REVIEW_TOKEN>`, compared in constant time.
  - If the token is unset, shorter than 32 characters, or equal to `SHAI_VERIFY_TOKEN` or `SHAI_META_APP_SECRET`, the review endpoints return 503 and stay disabled.
  - A wrong or missing token gets 401.
  - Only loopback clients are accepted unless `SHAI_REVIEW_ALLOW_REMOTE=1` is set.
- **Decisions:**
  - One decision per item, so a re-decision gets 409 `already_decided`. Re-sending the identical decision is idempotent.
  - The decisions table is append-only: SQLite triggers refuse UPDATE and DELETE, and held items can't be deleted.
  - Each decision is hash-chained (`prev_hash` → `hash`) and checked by `verify_decisions()` and `/review/audit`.
- **Approval sends nothing.** The approved status is `APPROVED_NOT_SENT`, every response carries `"sent": false`, and there is still no outbound code.

## Remaining gaps

- The rate limiter is in memory (it resets on restart) and per-process; there is no shared limit across replicas.
- Dropped (rate-limited) messages are not queued: they are lost by design.
- There is no outbound path (by design). Replies are never sent, even after approval.
- The review token is a single shared bearer secret, not per-person identity. `reviewer` is self-declared, so it records who claims to have decided; it is not verified. There is no TLS, so keep review on loopback. There is no retention or erasure policy for message text yet.
- `referee_adapter.review_numeric_fixture` creates its plan immediately before evaluating: fixture-only, not a compliant pre-registration.
- `maniac/audit.py` still leaks SQLite connections (3 ResourceWarnings in the full suite).
- Referee: 111000 COMPARE/LEARN, Δ BALANCE and the human-decision (`operator_id`) path are not implemented.
- There is no independent security review, and nothing is deployed.
