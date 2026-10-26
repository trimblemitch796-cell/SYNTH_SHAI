# SYNTH_SHAI V3.1 — Offline evidence bridge

**Status: research prototype; not an installed ChatGPT capability.** This adapter runs the existing `verification_v3.py` and `verification_v3_1.py` locally, and produces `144 HOLD` or `REVIEW_REQUIRED` only. Neither outcome permits real-world operations. All code is offline and has no ChatGPT connection or network access.

## Install in GitHub
Upload `shai_v31_bridge.py` and `test_shai_v31_bridge.py` to the **root** of `trimblemitch796-cell/SYNTH_SHAI`, ideally on a separate feature branch. Keep existing `verification_v3.py`, `verification_v3_1.py`, and `requirements.txt` from `main`. Optionally upload this documentation into `docs/V31_BRIDGE_README.md`. Create a pull request into `main` and wait for CI tests.

## Local run

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest -v test_shai_v31_bridge.py
python3 shai_v31_bridge.py --input /path/to/your/envelope.json --replay-db /path/to/protected/replay.sqlite \
    --trust-config /path/to/protected/trust.json --challenge <challenge-you-issued> --expected-sha256 <report-sha256>
```

The JSON input (envelope) must contain exactly `record`, which follows the V3.1 signed-evidence schema. Since 26 October 2026, trust material is **never** read from the envelope; an envelope with `trusted_keys`, `expected_sha256` or `expected_challenge` gives HOLD. The verifier supplies it separately: `--trust-config` is a protected local JSON file `{"trusted_keys": {...}}` mapping two pinned key IDs to `{ "source_id": "...", "public_key_hex": "64 lowercase hex characters" }`. `--challenge` is the challenge the verifier issued, and `--expected-sha256` is the report digest the verifier expects. In Python use `evaluate(envelope, db_path=..., trust=TrustConfig(...), expected_challenge=..., expected_sha256=...)`. In MANIAC, use `Supervisor(replay_db=..., trust=...)` and `issue_challenge(...)`. Private keys are never included. Do not commit authentic evidence, production keys, local databases, or sensitive data.

The output is `{"approval_granted": false, "decision": "REVIEW_REQUIRED"}` or `{"approval_granted": false, "decision": "144 HOLD"}`. Exit code 0 means *review required*, not safety approval. Exit code 2 means HOLD. A consumed challenge remains recorded in the SQLite file and cannot be replayed using the same database.

## SHAI gates
`000` PAUSE → `111` IDENTIFY → `222` OBSERVE_RAW → `333` DEFINE → `333000` RECORD → `777000` RECEIVE → `111000` COMPARE → `222000` RE-OBSERVE → `555000` TRIANGULATE → V3.1 signature/hash/replay check → `888000` LOOP CHECK → `999000` AUDIT → `444000` request HUMAN REVIEW. Failures → `144 HOLD`; `666000` RECOVERY and `1301133` REPAIR require a fresh verification with new evidence; `Δ` BALANCE is a conceptual decision review. These codes are project vocabulary; only the concrete cryptographic checks and replay DB are enforced by this bridge.

## Security boundaries
This is an offline prototype, **not a general-purpose security boundary, hosted API, ChatGPT plugin, or runtime enforcement layer**. The local trusted-key configuration, expected hash and challenge, SQLite database, filesystem, caller, and host must all be secured separately. The SQLite record is local; replay across devices is not prevented. No secret or key enrollment workflow is provided. Input size is limited for CLI file reads, while direct Python callers must apply their own limits. Review all changes and commission independent security testing before external integrations.
