# SYNTH_SHAI — WhatsApp Bridge + Deterministic Referee (offline integration prototype)

**NOT LIVE / NOT DEPLOYED / NOT INDEPENDENTLY REVIEWED.** No real AI provider integration, no outbound WhatsApp messages, no human-authentication or approval implementation. No changes have been pushed to GitHub by this package.

This is a **self-contained, additive GitHub-ready folder** joining two uploaded prototypes. It preserves each implementation in separate directories and adds a small **offline synthetic-fixture integration seam**. Do **not** copy its top-level README over the existing SYNTH_SHAI repository README; instead place these folders under a project subdirectory such as `integrations/whatsapp_referee_v1/` or open a dedicated branch/PR.

## Layout

- `whatsapp/bridge.py`: inbound-only Meta webhook signature verification and human-review HOLD draft; no outbound API.
- `whatsapp/referee_adapter.py`: offline-only numeric referee demonstration, **not invoked by webhook**.
- `referee/referee.py`: constrained deterministic exact-sum referee, audit journal, and no-approval outcomes.
- `test_integration.py`: demonstrates a synthetic 412-vs-421 disagreement resolves to checked 412 while retaining approval gate and never sending a message.
- `docs/`: original specifications/READMEs, retained for provenance.
- `.github/workflows/offline-tests.yml`: optional GitHub Actions tests; relocate this file to the repository's root `.github/workflows/` if integrating into the existing project.

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

`127.0.0.1:8080` is the default bind. Never commit real secrets. Do not publicly expose without secure HTTPS ingress, durable replay/idempotency controls, rate limits, identity authentication and independent review.

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
