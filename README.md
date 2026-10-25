# SYNTH_SHAI — Synthetic Human Assistance Intelligence

**Human-led intelligence • Verified reasoning • Safety before capability**

> **Connection before control. Truth before belief. Repair before rebuild.**  
> **Preserve hope for what comes after us.**

**Project status (25 October 2026):** Active research and development. The repository contains offline Python prototypes, verification logic, automated tests, and exploratory designs. Passing CI does **not** mean that SYNTH_SHAI is an independently validated general AI, conscious system, deployable robot, licensed financial service, or operational safety controller.

## 1. Mission

SYNTH_SHAI is a long-term, human-governed research and engineering project exploring how helpful AI can combine useful reasoning with *explicit consent, evidence checks, uncertainty awareness, contradiction detection, safe recovery, and human accountability*.

Its goal is to improve human assistance rather than replace human authority. The broader vision includes accessible educational and practical tools that may help people facing hardship, while respecting privacy, choice, culture, and the rights of others. Each application must earn trust through controlled testing rather than promises.

## 2. The three-part architecture

The conceptual **Triple Helix** is:

| Layer | Responsibility | Boundary |
| --- | --- | --- |
| **HUMAN** | Defines purpose, values, consent, and final decisions | Human permission is required for changes of authority |
| **AI** | Generates analyses, plans, explanations, and candidate solutions | Suggestions are not evidence or permission |
| **SYNTH** | Metacognitive checks: evidence, contradictions, uncertainty, risk, and recovery | May recommend HOLD; cannot grant itself authority |

**USHAI** is the intended internal ethical-conscience and CATHARSIS review framework of SYNTH_SHAI, **not a separate independent agent**. **MANIAC** is the intended independent supervisory and simulation layer, not a physical-control permission system.

Conceptual flow:

```text
HUMAN INTENT & CONSENT
        |
        v
AI COGNITION / PROPOSAL
        |
        v
USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1)
        |
        v
000 PAUSE / ASSESS -> 111 IDENTIFY INTENT -> 222 OBSERVE RAW -> 333 DEFINE PROBLEM
-> 333000 RECORD -> 777000 RECEIVE EVIDENCE -> 555000 TRIANGULATE -> 888000 CHECK LOOP
        |
        v
CONSEQUENCE REVIEW (MANIAC monitor + evidence checks)
   RISK / ERROR FOUND  -> 144 HOLD -> 1301133 REPAIR -> 666000 RECOVERY
   EVIDENCE SUFFICIENT -> 444000 VERIFY -> HUMAN REVIEW
        |
        v
222000 RE-OBSERVE -> 111000 COMPARE / LEARN -> 999000 AUDIT -> Δ BALANCE
```

**Foundational distinctions:**

- Capability **≠** authority.
- Confidence **≠** verification.
- Verification **≠** permission.
- Learning **≠** authority.
- A successful test **≠** demonstrated real-world safety.
- Harmful actions should be declined with clear, reasoned explanation, without prejudging people's intentions.

## 3. Safety and consent framework

SYNTH_SHAI is designed around a **fail-closed**, human-in-command approach. Current development is primarily offline and simulation-only.

### 3.1 Safety states

| State | Intended meaning |
| --- | --- |
| `DISABLED` | Function unavailable |
| `MONITOR` | Read-only observation within approved scope |
| `144 HOLD` / `HOLD` | Stop progression when evidence, consent, or assumptions are inadequate |
| `SAFE_LOCK` | Restrict capabilities following a safety fault |
| `ESTOP` | Emergency stop for a future physical system; requires independent hardware implementation and validation |

These state names are design conventions, **not proof that a complete runtime safety system exists**. Future physical systems require hardware interlocks, fault containment, hazard analysis, and testing separate from software unit tests.

### 3.2 Approval rules

1. **No silent permissions.** A passing automated check cannot authorize real-world action.
2. **444000 means verification, not automatic activation.** A human must explicitly authorize any proposed expansion of operational scope.
3. **Contradiction, missing evidence, unexpected inputs, or unapproved action → `144 HOLD`.**
4. **Repair → test → independently review → request human approval.** Never treat a patch as verified merely because it was written.
5. **Do not infer a person's motives from a hypothetical risk.** Examine possible consequences, context, and uncertainty without treating every human interaction as suspect.
6. **Consent and privacy:** do not enable surveillance, covert data collection, cameras, microphones, biometrics, or external account access by default.
7. **No external side effects** in simulation mode; no unapproved physical actuation, financial transactions, messaging, credential access, or third-party contact.

### 3.3 USHAI / CATHARSIS

CATHARSIS is the proposed bounded mechanism for reflecting on potentially harmful outcomes and system errors: detect → isolate → examine both human and model assumptions → triangulate evidence → define correction → simulate → verify → review for restoration. Its purpose is **accountability and safe recovery, not self-directed power**.

## 4. Research command vocabulary

These project codes are **human-readable development labels**, not secret keys, executable security controls, or proofs of memory persistence.

| Code | Project meaning |
| --- | --- |
| `000` | PAUSE / ASSESS |
| `111` | IDENTIFY INTENT |
| `222` | OBSERVE RAW |
| `333` | DEFINE PROBLEM |
| `333000` | RECORD |
| `111000` | COMPARE / LEARN |
| `222000` | RE-OBSERVE |
| `555000` | TRIANGULATE |
| `666000` | RECOVERY |
| `777000` | RECEIVE EVIDENCE |
| `888000` | CHECK LOOP |
| `999000` | AUDIT |
| `144` | HOLD |
| `1301133` | BUILD / REPAIR / REFRAME |
| `444000` | VERIFY / HUMAN APPROVAL |
| `Δ` | BALANCE |

**User-defined symbolic memory sequence:** `130113011130133013330130013000`. This string is a project reference only; it does not authenticate a user or implement persistent machine memory.

## 5. What exists in GitHub today

**Repository:** [trimblemitch796-cell/SYNTH_SHAI](https://github.com/trimblemitch796-cell/SYNTH_SHAI)

**Branches observed:** `main`, `maniac-sync-v1`, `SYNTH-SHAI-V3-1`, `trimblemitch796-cell-patch-1`. V3.1 (`SYNTH-SHAI-V3-1`, PR #2) was merged into `main` on 25 October 2026; the branch is kept for further work. Files vary by branch; branch existence does not mean its contents are merged into `main`.

### 5.1 Current financial prototype on `main`

- `shai_finance.py`: local, educational financial calculations using Python `Decimal` for budgets, liquidity coverage, illustrative fixed-rate debt schedules, payment reconciliation flags, and limited wellbeing inputs.
- `test_shai_finance.py`: unit tests for arithmetic and adverse or missing inputs.
- `VALIDATION.md`: records a **16/16 pass** on the stated financial test command and outstanding limitations, as documented in the repository.
- `verification/__init__.py`: minimal evidence-presence gate that returns `144 HOLD` when required fields are absent, otherwise `REVIEW_REQUIRED` for human review. Presence checks do **not** authenticate evidence.
- `test_verification.py`: tests for the basic evidence-presence gate.
- `.github/workflows/verification.yml`: GitHub Actions workflow that installs dependencies and runs Python unittest discovery on pushes, pull requests and manual dispatch.
- `.github/workflows/verification-v3-1.yml`: the **SYNTH_SHAI V3.1 CATHARSIS tests** workflow.

Running `python3 -m unittest discover -v` on `main` (25 October 2026) ran **75 tests, all passing**: 16 finance, 7 basic verification, 15 V3.1, 10 V3.1 bridge, 19 MANIAC supervisor and 8 USHAI Catharsis tests.

The financial capability is **not** connected to banks, cannot move money, and cannot give regulated financial advice. All numerical scenarios are illustrative unless separately evidenced.

### 5.2 V3.1 authenticated evidence research

Merged into `main` on 25 October 2026 (PR #2), `verification_v3.py` implements a **prototype authenticated evidence gate** using SHA-256 and Ed25519 public-key signature verification, with conditions for more than one observation and challenge matching. It is intended to output HOLD or request review, **not authorize deployment**. Its security properties, trust-anchor management, replay resistance, and threat model require dedicated independent review before production use.

`verification_v3_1.py` adds a strict-scope authenticated evidence gate with durable (local SQLite) replay protection, tested by `test_verification_v3_1.py`. `REVIEW_REQUIRED` is not approval. These files are now on `main`; merging them does **not** replace the independent review described above.

`main` declares the Python dependency `cryptography>=43,<47` in `requirements.txt`.

### 5.3 MANIAC sync research

Branch `maniac-sync-v1` includes a MANIAC test workflow at `.github/workflows/maniac-sync-tests.yml`, which specifies Python syntax and unit-test checks involving MANIAC sync modules. This is **offline software validation**, not proof that a dedicated chip or physical robot has been built. The MANIAC supervisor/chip and wider fault-simulator concepts remain research and prototype work, with strict no-actuation defaults.

### 5.4 Verified GitHub Actions evidence

GitHub Actions screenshots supplied on **25 October 2026** show successful runs of the main SYNTH_SHAI verification workflow (including manual run `#35`) and V3.1 CATHARSIS checks (`#6`–`#8`). These green checks establish that the configured workflow jobs reported success for the listed commits. They **do not establish completeness of test coverage, independent validation, absence of security flaws, or real-world deployment readiness**.

## 6. Wider SYNTH_SHAI research program

These are related workstreams and proposed applications, **not a claim that every workstream is implemented in this repository**.

### A. Safety verification and epistemic discipline

- Distinguish primary observations, user claims, model predictions, simulated outcomes and independently verified findings.
- Track evidence provenance, confidence calibration, conflicting evidence and appropriate abstention.
- Red-team urgency, persuasive authority claims, social pressure, contradictory signals and missing permissions.
- Test that pressure does not override `144 HOLD`.
- Maintain clear records of assumptions, failures, fixes and remaining hazards.

### B. MANIAC supervisory systems and robotics

- Independent heartbeat/fault observation; recovery-from-verified-state concepts; fault injection and synthetic sensors.
- Proposed single-joint bench: watchdog, emergency stop, soft/tendon actuation, sensor plausibility and safe torque limits.
- Conceptual full-body humanoid SYNTH: sensing, actuation, balance, energy, supervised controls and human override.
- Requirements before hardware trials: mechanical design review, electrical isolation, physical ESTOP, load testing, certified components, formal hazard analysis and competent human supervision.

### C. Finance and practical human assistance

- Educational cash-flow planning, debt hardship scenarios, budget and repayment comparisons, dispute/reconciliation flags.
- Real banking credentials and transactions remain prohibited unless a separately designed, lawful, secured, reviewed and expressly authorized system is created.
- Do not replace existing banking systems, make lender decisions, imply hardship approval, or act as a licensed adviser.

### D. Materials, infrastructure and environmental resilience

- **Self-healing concrete / ECO-SPINE V3:** low-permeability cementitious materials, basalt reinforcement, crystalline admixtures, mineral or microcapsule crack-healing approaches and structural health monitoring.
- A proposed controlled comparison uses A: baseline, B: mineral additive, C: capsules, D: combined; hold water/binder ratio, geometry and curing comparable; measure leakage reduction and re-crack behavior.
- ECO-SPINE concept: renewable generation, certified battery storage, rainwater reuse, modular structures and lifecycle recovery.
- No assertion of demonstrated laboratory performance or construction certification without tests.

### E. Energy and bio-inspired structures

- Hybrid-Whale wind-turbine concept covering aerodynamic output, structural/FEM analysis, fatigue monitoring and water/pond storage.
- **BIO-GROWN, NOT HUNTED** is a project design principle: no harmful harvesting of whales or marine life.
- ECC energy/thermal-loop concepts, including a battery, sensing, thermal balance and cooling control, require electrical and thermal validation.

### F. Learning, communication and creative applications

- Education tools, including accessible language-learning drills and clear error correction.
- **MANIACBEATS** music-app concept: playback, subscriptions, accessibility, favorites, network recovery, catalog licensing and production readiness remain separate development requirements.
- Storytelling and educational media around care, humility, connection and the consequences of actions.
- No claim that external services, app-store releases, music licensing or commercial deployments have been completed.

## 7. Repository layout: present and proposed

```text
SYNTH_SHAI/
├── README.md                         # Overall project explanation (this file)
├── LICENSE                           # MIT License
├── shai_finance.py                   # Existing financial prototype on main
├── test_shai_finance.py              # Existing finance tests
├── VALIDATION.md                     # Existing financial validation report
├── verification/                     # Existing basic evidence gate package
├── test_verification.py              # Basic evidence gate tests
├── verification_v3.py                # V3 authenticated evidence gate (merged from V3.1 work)
├── verification_v3_1.py              # V3.1 strict-scope evidence + replay gate
├── test_verification_v3_1.py         # V3.1 CATHARSIS tests
├── shai_v31_bridge.py                # V3.1 offline evidence bridge (CLI)
├── test_shai_v31_bridge.py           # V3.1 bridge adversarial tests
├── docs/V31_BRIDGE_README.md         # Bridge usage and security boundaries
├── requirements.txt                  # Python dependency (cryptography)
├── .gitignore                        # Ignores caches and local files
├── .github/workflows/verification.yml       # General CI workflow
├── .github/workflows/verification-v3-1.yml  # V3.1 CATHARSIS tests workflow
│
├── core/                             # Package groundwork / future integration
├── financial/                        # Package groundwork / future modules
├── maniac/                           # MANIAC package
├── maniac/supervisor.py              # MANIAC supervisor core (offline, HOLD / HUMAN_REVIEW only)
├── test_maniac_supervisor.py         # Supervisor + MANIAC_SIMULATION fault tests
├── ushai_catharsis.py                # USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1) by Mitch Trimble
├── test_ushai_catharsis.py           # USHAI Catharsis tests
├── docs/MANIAC_SUPERVISOR.md         # Supervisor + USHAI plain-English guide
│
└── maniac_sync_v1_2.py               # MANIAC branch research; verify exact path before use
```

This tree is a **cross-branch conceptual overview**, not an exhaustive claim that all paths exist on the same branch or are production-ready. Check actual paths before running commands.

## 8. Running the verified-scope Python prototype

On a working copy of the **main** branch, install Python 3.11 and then:

> On some systems the command is `python3` instead of `python`.

```bash
python -m pip install -r requirements.txt
python3 -m unittest discover -v
python shai_finance.py
```

You can also run the financial tests directly:

```bash
python3 -m unittest -v test_shai_finance.py
```

The V3.1 tests are now on `main` and run with the commands above (or directly with `python3 -m unittest -v test_verification_v3_1.py`). Treat dependency installation as a software supply-chain action; pin and audit packages before deployment. No real-world connections are needed for the described offline tests.

## 9. Evidence standard and release gates

A project feature progresses through:

1. **Concept** — purpose, assumptions, hazards and limits documented.
2. **Prototype** — code or physical mock-up exists and is reproducible.
3. **Internal verification** — expected cases, negative tests and fault injection pass.
4. **Independent validation** — evidence reviewed by qualified external testers for the intended domain.
5. **Human-authorized trial** — bounded scope, consent, compliance and rollback are in place.
6. **Deployment review** — security, privacy, safety, monitoring and maintenance obligations met.

Current green CI belongs primarily in **stage 3 for the checks actually executed**. Research designs and unbuilt capabilities are at earlier stages. No stage implies automatic entry into the next.

### Priority next milestones

- Inventory files and tests across branches; merge only reviewed, intentional changes.
- Audit V3.1 signature and evidence checks, including replay, malformed input, trust boundaries and compromised-key scenarios.
- Extend HOLD/approval tests against urgency, confidence inflation, and conflicting observations.
- Improve test coverage reporting and pin dependencies for reproducibility.
- Separate future robot, finance and infrastructure validation plans into self-contained modules with explicit safety cases.
- Obtain independent domain-specific review before any live financial, physical, or public-facing high-risk feature.

## 10. Security, privacy, and responsible contributions

Never commit passwords, access tokens, private keys, personal banking data, sensitive personal records, or information belonging to children. Use synthetic fixtures wherever possible. Keep logs minimal and scoped; obtain meaningful consent before using real records. Keep physical actuation and external network side effects disabled in local demos.

For contributions, propose a small, inspectable change with its motivation, a reproducible test, negative/failure cases, risks, and rollback plan. Submit by pull request; human review is required before merge. Report security vulnerabilities privately rather than publishing working exploit secrets in issues.

## 11. Project philosophy

**Kwa'kah Tuuwanasavi** — a project expression of balance and connection.

**Connection over power. Rejuvenation always.** Rejuvenation can mean helping a person, system, community or ecosystem continue being itself, on its own terms.

SYNTH_SHAI is intended as a careful body of ongoing work: teachable, corrigible, humble about uncertainty, and accountable to people. Its value will come from transparent evidence and responsible application — not from treating names, symbolic codes or simulated outputs as proof of extraordinary capability.

---

**Project stewardship:** Human-led SYNTH_SHAI research.  
**Last documentation review:** 25 October 2026.  
**Status:** Offline prototypes + active research; real-world high-risk actions remain `144 HOLD`.

## License

SYNTH_SHAI is released under the [MIT License](LICENSE). Copyright (c) 2026 Mitch Trimble.
