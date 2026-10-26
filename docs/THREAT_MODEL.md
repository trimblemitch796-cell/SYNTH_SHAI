# SYNTH_SHAI threat model: what it does and doesn't protect against

*Written 26 October 2026 against `main` at `31f617a`. Plain-English version for a hobbyist owner. Re-check the file references when the code changes.*

## 1. Scope and status

- SYNTH_SHAI is an **offline research prototype**. It is a set of Python modules plus tests and simulations that run on one computer.
- It is **not a medical device**. `synth_shai_doctor/` is simulation-only and uses synthetic data only.
- It is **not for real hardware yet**. The SHAI twin (`shai/twin.py`) moves simulated joints only. Step 8 (hardware) is waiting for a contractor, and needs the separate hardware safety work listed in README.md.
- It makes no network calls and never approves anything by itself: `approval_granted` is always False.

## 2. What we are protecting (assets)

| Asset | Why it matters |
|---|---|
| **Human consent and approval** | Nothing should move or proceed unless a human said yes to *this exact* thing, within scope and before expiry. |
| **The 144 HOLD decision** | When something is wrong, the system must stop and stay stopped ("fail closed"), not be talked or tricked out of it. |
| **The audit trail** | A trustworthy record of what was decided, by whom and why (`999000 AUDIT`). |
| **Evidence integrity** | Sensor readings and signed evidence must be real, fresh, consistent and not reused. |

## 3. Trust assumptions (what we assume is honest)

- **Trusted:** the Python process running SYNTH_SHAI, all the code loaded into it, the operating-system user it runs as, and the machine's disk.
- **Trusted:** the operator (the human who approves) is honest and is who they say they are.
- **Trusted:** whoever constructs `Supervisor(replay_db=...)` / `ShaiTwin(replay_db=...)` and picks file paths.
- **Untrusted:** everything that arrives as *data*: sensor readings, evidence bundles and envelopes, consent records, approval payloads, motion plans, request fields.

In short: SYNTH_SHAI defends against **bad or hostile data passing through it**. It does **not** defend against **hostile code or users on the same computer**.

## 4. Threat table

"In scope?" means: is this something the current design *tries* to stop?

| Threat | In scope? | What SYNTH_SHAI does today | Where | Known gap |
|---|---|---|---|---|
| Faulty, stale, NaN/inf, stuck or out-of-range sensor readings | Yes | Rejects non-finite or non-numeric values, out-of-range values, readings older than 2 s or from the future, and a stuck history (same value 5 times). Any one gives 144 HOLD. | `maniac/evidence.py` (`_check_sensors`), `maniac/monitor.py` | Thresholds are illustrative, not engineered for a real robot. |
| Contradicting sensors / single source | Yes | Requires two or more sources of different types that agree within 5%; otherwise HOLD. | `maniac/evidence.py`, `maniac/triangulate.py` | Two sensors that are wrong *in the same way* would still agree. |
| Forged or tampered provenance (signed evidence) | Partly | The V3.1 gate checks Ed25519 signatures from 2 sources, the report's SHA-256 and the challenge, and fails closed to HOLD. | `verification_v3_1.py`, `shai_v31_bridge.py` | **The trusted public keys, expected hash and expected challenge travel *inside the same envelope* as the evidence** (`shai_v31_bridge.evaluate`). This catches edits to a signed envelope, but anyone who makes their own keys and signs their own envelope passes. Real trust needs keys pinned in trusted configuration. |
| Replayed evidence | Yes (same store) | Each challenge is recorded once in a SQLite replay database, so the same evidence a second time gives HOLD. The database path comes from trusted configuration; a request-supplied `db_path` is refused. | `verification_v3_1.py`, `maniac/evidence.py` (`make_bridge_checker`), `maniac/supervisor.py` | Only within **one** replay database. Because the challenge is chosen by the envelope (see row above), *new* self-signed evidence is not a "replay". There is no cross-device replay protection. |
| Replayed or forged approvals (twin motion) | Partly | An approval must carry the request ID and the SHA-256 of the exact plan. It is checked before the loop and again right before motion, and is single-use. A mismatch, ID-only approval or reuse gives HOLD. | `shai/twin.py` (`plan_digest`, `approval_for`, `_approval_matches`) | Approvals are plain dictionaries with **no cryptographic identity**: any code can build a valid-looking one with `approval_for(...)`. Single-use tracking is in memory per twin, so a fresh `ShaiTwin` doesn't remember past approvals. |
| Missing, expired or out-of-scope consent | Yes | Consent must exist, have a finite expiry in the future, and explicitly list the action (deny by default). The twin re-checks consent before every motion step. | `maniac/evidence.py` (`_check_permissions`), `shai/twin.py` | Consent is also a plain dictionary; nothing proves a real human wrote it. |
| Forged `VerifyResult` (skipping the gates) | Yes, in-process | Only results issued by `consequence_review` are "genuine"; hand-built ones can't record a decision or reach BALANCED. | `maniac/verify.py` (`_issue`, `is_genuine`), `maniac/balance.py` | An in-process registry, not a cryptographic seal: code that edits module internals (e.g. `_GENUINE`) can defeat it. |
| Tampered human decision after recording | Yes, in-process | The recorded decision and its fields are remembered; a forced `object.__setattr__` swap or edit is detected and gives HOLD, and re-recording is refused. | `maniac/verify.py` (`decision_intact`), `maniac/balance.py` | Same limit: hostile in-process code can edit `_RECORDED` too. |
| Missing operator identity in the audit | Yes | The `HUMAN REVIEW` audit entry records `operator_id`, reason and plan digest. An empty or missing operator gives HOLD. | `maniac/loop.py` (`human_review_detail`) | `operator_id` is just text the caller supplies; it isn't authenticated. |
| Audit: editing an entry inside the chain | Yes | Each entry's hash covers the previous hash, so edits break the chain; a broken chain gives UNBALANCED/HOLD and SQLite loads refuse it. | `maniac/audit.py` (`verify_chain`), `maniac/balance.py` | — |
| Audit: deleting the tail (last entries) | Yes (partly) | The SQLite store keeps a count/head anchor that is checked on load and append, so deleting tail rows alone is detected. `expected_head` gives a stronger check. | `maniac/audit.py` (`_check_anchor`) | Deleting entries **and** the anchor together is undetected unless you kept `expected_head` somewhere else. An older database is anchored on first open (trust on first use). |
| Audit: full rewrite with recomputed hashes | **No** | Nothing. The hashes are not signed, so anyone who can write the file can rebuild a valid-looking chain. | `maniac/audit.py` docstring says so | Needs signed entries and/or an external anchor (roadmap). |
| Same-process monkey-patching (replacing gate functions or flipping state in memory) | **No** | Nothing can stop this in one Python process; the in-process guards above raise the bar only slightly. | Whole codebase (single process) | Needs out-of-process execution or sandboxing (roadmap). |
| Separate-process races (two programs using the same files at once) | **Not tested** | SQLite transactions (`BEGIN IMMEDIATE`) guard the replay and audit stores, and a stale audit writer must reload. | `verification_v3_1.py`, `maniac/audit.py` | The concurrency tests use **threads in one process** (`ThreadPoolExecutor` in `test_v31_concurrent_replay.py` and `test_issue10_persistence_concurrency.py`). Multi-process behaviour is untested. |
| Malicious local user or root | **No** | Nothing. They can read and edit the code, the databases and the audit file. | — | Out of scope for a local prototype; would need OS permissions, separate accounts and external anchoring. |
| Compromised dependencies (e.g. `cryptography`) | Partly | Hash-pinned lock file, a `dependency-advisories` CI job (pip-audit) and a `reachable-history-secrets` job (gitleaks). Actions are pinned to commit SHAs. | `requirements-lock.txt`, `.github/workflows/release-security.yml` | Advisory scans only find *known* problems; a malicious new release or a compromised build machine isn't covered. |
| Network attacks | N/A | The prototype makes no network calls. | — | Becomes in scope the moment anything is networked. |

## 5. What SYNTH_SHAI does NOT protect against

Said plainly:

- **Code running in the same Python process.** It can replace any gate, flip any flag, or edit any registry. All the in-process checks assume the code itself is honest.
- **Anyone who can write to the computer's files as the same user, or as root.** They can delete or rewrite the audit and replay databases, and recompute every hash.
- **Fake people.** Approvals, consent and `operator_id` are not tied to a cryptographic identity. Any program can build one that looks valid.
- **Self-signed evidence.** The V3.1 envelope carries its own trusted keys and challenge, so the signature check proves the envelope wasn't edited, not who made it.
- **Several processes or several devices at once.** This is not tested and not designed for.
- **Real-world hazards.** This is offline simulation only: no timing guarantees, no real sensors, no physical emergency stop.

## 6. Roadmap (none of this is done yet)

| Item | Status |
|---|---|
| This threat model | Proposed in this PR (not yet reviewed) |
| Ed25519-signed consent, approvals and audit entries, with operator keys pinned in trusted config | Not done |
| Pin V3.1 trusted keys and challenges in trusted configuration instead of inside the envelope | Not done |
| External anchoring of the audit head (e.g. a copy kept on another machine or service) | Not done |
| Out-of-process execution / sandbox, with gates in a separate process or OS user | Not done |
| Adversarial tests: fuzzing, cross-process race tests, deliberate monkey-patching tests | Not done |

## 7. Credit and corrections

Prompted in part by an AI-assisted review (Gemini, 26 Oct 2026). Its points about single-process patching, local audit rewriting, untested cross-process concurrency and consent without cryptographic identity are reflected above.

Corrections to that review:
- **Comparison baselines.** It said `docs/FAIR_COMPARISON.md` compares SYNTH_SHAI against enterprise cloud safety suites. **It doesn't.** The baselines are a conventional emergency stop + watchdog and a plain human-approval gate, run offline on the same 33 scenarios.
- **Replay.** Its replay point is mostly already handled: replayed evidence (same challenge, same store) and replayed or plan-mismatched approvals both give HOLD. The real remaining gap is the self-supplied keys and challenge described in section 4.

This document is the author's own assessment and is **not** an independent review; see [INDEPENDENT_REVIEW_HANDOFF.md](INDEPENDENT_REVIEW_HANDOFF.md).
