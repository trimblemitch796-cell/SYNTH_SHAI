# SYNTH_SHAI — Synthetic Human Assistance Intelligence

**Human-led intelligence • Verified reasoning • Safety before capability**

**Start here:** [Verified Core Inventory](docs/VERIFIED_CORE.md) — a concise
list of what has offline test evidence, what remains design-only, and what
cannot yet be sold or deployed as a secure service.

> **Connection before control. Truth before belief. Repair before rebuild.**  
> **Preserve hope for what comes after us.**

**Project status (27 October 2026):** Active research and development. The repository contains offline Python prototypes, verification logic, automated tests, and exploratory designs. Passing CI does **not** mean that SYNTH_SHAI is an independently validated general AI, conscious system, deployable robot, licensed financial service, or operational safety controller.

**Public research code only:** SYNTH_SHAI is not a hosted AI service, not a financial adviser, not an autonomous robotics controller, and not a medical device.

**V2–V4 execution-boundary correction (1 November 2026) — 144 HOLD:** Signed-administrator, default-deny dispatch, separate-process worker and Linux resource-limit prototypes remain **offline research implementations**. Resource limits do **not** establish a complete security sandbox, trusted operator identity, filesystem or network isolation, or permission for live execution. Passing project-maintained tests does **not** constitute an independent audit or deployment authorization. **Consequential use remains at `144 HOLD`** pending independent review and explicit human authorization. See [the verified-core inventory](docs/VERIFIED_CORE.md) and [threat model](docs/THREAT_MODEL.md).

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
HUMAN (purpose, values, consent)
        |
        v
SYNTH_SHAI AI cognition engine
        |
        v
USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1)
        |
        v
000 PAUSE / ASSESS -> 111 IDENTIFY INTENT -> 222 OBSERVE RAW -> 333 DEFINE PROBLEM
-> 333000 RECORD -> 777000 RECEIVE EVIDENCE -> 555000 TRIANGULATE -> 888000 CHECK LOOP
        |
        v
CONSEQUENCE REVIEW (MANIAC monitor + CHECK EVIDENCE + TRIANGULATE)
   RISK / ERROR FOUND  -> 144 HOLD -> 1301133 BUILD / REPAIR / REFRAME -> 666000 RECOVERY
   EVIDENCE SUFFICIENT -> 444000 VERIFY / HUMAN APPROVAL -> HUMAN REVIEW
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

**Threat model:** what SYNTH_SHAI does and doesn't protect against is in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

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
| `777000` | RECEIVE EVIDENCE |
| `555000` | TRIANGULATE |
| `888000` | CHECK LOOP |
| `144` | HOLD |
| `1301133` | BUILD / REPAIR / REFRAME |
| `666000` | RECOVERY |
| `444000` | VERIFY / HUMAN APPROVAL |
| `222000` | RE-OBSERVE |
| `111000` | COMPARE / LEARN |
| `999000` | AUDIT |
| `Δ` | BALANCE |

**User-defined symbolic memory sequence:** `130113011130133013330130013000`. This string is a project reference only; it does not authenticate a user or implement persistent machine memory.

## 5. What exists in GitHub today

**Repository:** [trimblemitch796-cell/SYNTH_SHAI](https://github.com/trimblemitch796-cell/SYNTH_SHAI)

**Branches:** `main` holds all merged work: V3.1 (PR #2), the bridge (PR #5), MANIAC steps 1–5 and hardening (PRs #11–#16), clean-up (PR #20), V25 TRI5 (PRs #17–#18), V3.1 concurrent replay tests (PR #19), the full loop (PR #22), Super Tool V1 (PR #23), and the SHAI digital twin/power model. `maniac-sync-v1` is an unmerged research branch. See [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md) for the current milestone record.

### 5.1 Finance prototype and basic evidence gate

- `shai_finance.py`: local, educational financial calculations using Python `Decimal` for budgets, liquidity coverage, illustrative fixed-rate debt schedules, payment reconciliation flags, and limited wellbeing inputs.
- `test_shai_finance.py`: unit tests for arithmetic and adverse or missing inputs.
- `VALIDATION.md`: records a **16/16 pass** on the stated financial test command and outstanding limitations, as documented in the repository.
- `verification/__init__.py`: minimal evidence-presence gate that returns `144 HOLD` when required fields are absent, otherwise `REVIEW_REQUIRED` for human review. Presence checks do **not** authenticate evidence.
- `test_verification.py`: tests for the basic evidence-presence gate.
- `.github/workflows/verification.yml`: GitHub Actions workflow that installs dependencies and runs Python unittest discovery on pushes, pull requests and manual dispatch. A second job runs the same suite on Python 3.13 with `-W error::ResourceWarning`, so the SQLite leak guard can actually detect leaks (CPython 3.11 does not emit those warnings).
- `.github/workflows/verification-v3-1.yml`: the **SYNTH_SHAI V3.1 CATHARSIS tests** workflow.

**Local verification, 26 October 2026 (with pinned evidence keys applied):** `python3 -m unittest discover -q` passes **442 tests**, and `python3 -m maniac.simulation` passes **33/33 scenarios**. An offline, author-written comparison against two conventional baselines is in [docs/FAIR_COMPARISON.md](docs/FAIR_COMPARISON.md) (`python3 -m maniac.benchmark`); it is not independent evidence of superiority. Coverage includes finance, evidence and replay gates, MANIAC/USHAI, recovery and loop closure, SHAI twin/power, V25 TRI5 and Super Tool V1, including durable-audit, loop-level safeguarding, power/consent and release-security regressions. These historical local results used the workspace's preinstalled cryptography 50.0.0. Subsequent GitHub Actions on PR #48's merge commit confirmed 442 passing tests and installed the committed lock (cryptography 50.0.2, cffi 2.1.1 and pycparser 3.12); see section 5.4. Both local and CI results remain offline, project-maintained evidence, not independent validation. Rerun the commands for the revision under review.

The financial capability is **not** connected to banks, cannot move money, and cannot give regulated financial advice. All numerical scenarios are illustrative unless separately evidenced.

### 5.2 V3.1 authenticated evidence research

Merged into `main` on 25 October 2026 (PR #2), `verification_v3.py` implements a **prototype authenticated evidence gate** using SHA-256 and Ed25519 public-key signature verification, with conditions for more than one observation and challenge matching. It is intended to output HOLD or request review, **not authorize deployment**. Its security properties, trust-anchor management, replay resistance, and threat model require dedicated independent review before production use.

`verification_v3_1.py` adds a strict-scope authenticated evidence gate with durable (local SQLite) replay protection, tested by `test_verification_v3_1.py`. `REVIEW_REQUIRED` is not approval. These files are now on `main`; merging them does **not** replace the independent review described above.

`requirements.txt` includes the exact, hash-checked dependency set in `requirements-lock.txt`: cryptography 50.0.2, cffi 2.1.1 and pycparser 3.12. See [third-party notices](THIRD_PARTY_NOTICES.md) for the dependency upgrade and license evidence.

### 5.3 MANIAC, USHAI and V25 TRI5 (offline simulation on `main`)

These modules are **offline simulations that control no hardware**. They only return `144 HOLD`, `HUMAN_REVIEW` (or for V25 TRI5 `URGENT_HUMAN_HELP`), and `approval_granted` is always False.

- `ushai_catharsis.py`: USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1), written by Mitch Trimble.
- `maniac/`: supervisor, MONITOR SYSTEM, CHECK EVIDENCE, 555000 TRIANGULATE, 444000 VERIFY / HUMAN APPROVAL, 1301133 BUILD / REPAIR / REFRAME, 666000 RECOVERY, 222000 RE-OBSERVE, 111000 COMPARE / LEARN, 999000 AUDIT, Δ BALANCE (`run_loop`) and MANIAC_SIMULATION (`python3 -m maniac.simulation`). See [docs/MANIAC_SUPERVISOR.md](docs/MANIAC_SUPERVISOR.md).
- `synth_shai_doctor/`: AAA Doctor V1, a **simulation-only**, synthetic-data-only escalation rule layer. It is not a medical device and makes no diagnosis or dispatch. In an emergency in Australia, call 000. See [synth_shai_doctor/README.md](synth_shai_doctor/README.md).
- `shai/`: SHAI digital twin and ELO-ECTRIC power model. These are **software-only, use illustrative numbers and are not hardware-ready**. Joints move only through MANIAC `run_loop()` plus an explicit human approval. See [docs/SHAI_DIGITAL_TWIN.md](docs/SHAI_DIGITAL_TWIN.md).
- `v25_tri5.py`: V25 TRI5 child-safeguarding advisory gate, an extra conservative layer after MANIAC/USHAI that never overrides a HOLD. The offline loop supports opt-in assessment via `safety_signals`. See [docs/V25_TRI5.md](docs/V25_TRI5.md).
- Release evidence and boundaries: [docs/V31_RELEASE_VERIFICATION.md](docs/V31_RELEASE_VERIFICATION.md).

The separate `maniac-sync-v1` branch holds earlier MANIAC sync research and is **not merged**.

### 5.4 Verified GitHub Actions evidence

**Checked 27 October 2026:** PR #48 merged as `406440d32eb4aa4ffb3d2e0622aa831ef9600745`. [Verification run 40301085939](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40301085939) reports 442 tests passed, including all 33 offline scenarios and the benchmark/report equality check. [V3.1 run 40301085852](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40301085852) passes its 15-test subset; [release-security run 40301085774](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40301085774) reports both security jobs successful. The locked installation succeeded with cryptography 50.0.2, cffi 2.1.1 and pycparser 3.12 on Python 3.11.17. These are project-maintained checks of the named revision, not an independent review or deployment approval. See the [release evidence reconciliation](docs/RELEASE_SECURITY_CHECKLIST.md#pr-48-evidence-reconciliation--27-october-2026).

**Historical evidence:**

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
├── CONTRIBUTING.md / SECURITY.md     # How to contribute / report security issues
├── VALIDATION.md                     # Financial validation report
├── requirements.txt                  # Python dependency (cryptography)
├── .gitignore                        # Ignores caches, local databases and OS files
├── .github/workflows/                # CI: verification.yml, verification-v3-1.yml
│
├── shai_finance.py                   # Financial prototype
├── test_shai_finance.py
├── verification/                     # Basic evidence-presence gate package
├── test_verification.py
├── verification_v3.py                # V3 authenticated evidence gate
├── verification_v3_1.py              # V3.1 strict-scope evidence + replay gate
├── test_verification_v3_1.py
├── test_v31_concurrent_replay.py     # V3.1 concurrent / durable replay tests
├── shai_v31_bridge.py                # V3.1 offline evidence bridge (CLI)
├── test_shai_v31_bridge.py
│
├── ushai_catharsis.py                # USHAI ETHICAL CONSCIENCE (CATHARSIS V1.1) by Mitch Trimble
├── test_ushai_catharsis.py
├── maniac/
│   ├── supervisor.py                 # Supervisor core (HOLD / HUMAN_REVIEW only)
│   ├── monitor.py                    # MONITOR SYSTEM: heartbeats, watchdog, faults, SAFE_LOCK
│   ├── evidence.py                   # CHECK EVIDENCE: sensors, contradictions, consent, provenance
│   ├── triangulate.py                # 555000 TRIANGULATE
│   ├── verify.py                     # 444000 VERIFY / HUMAN APPROVAL (CONSEQUENCE REVIEW)
│   ├── chain.py                      # monitor -> evidence -> triangulate -> verify in one call
│   ├── recovery.py                   # 1301133 BUILD / REPAIR / REFRAME + 666000 RECOVERY
│   ├── observe.py                    # 222000 RE-OBSERVE
│   ├── learn.py                      # 111000 COMPARE / LEARN (append-only, only ever stricter)
│   ├── audit.py                      # 999000 AUDIT hash chain
│   ├── balance.py                    # Δ BALANCE
│   ├── loop.py                       # run_loop(): the whole flow end to end
│   └── simulation.py                 # MANIAC_SIMULATION fault injector
├── test_maniac_supervisor.py, test_maniac_hardening.py, test_maniac_monitor.py,
│   test_maniac_evidence.py, test_maniac_triangulate.py, test_maniac_verify.py,
│   test_maniac_simulation.py, test_maniac_loop.py
├── shai/
│   ├── twin.py                       # SHAI digital twin (simulated 170 cm humanoid, example values)
│   └── power.py                      # ELO-ECTRIC power model (2 kWh pack, reserve, heat)
├── test_shai_twin.py, test_shai_power.py
├── v25_tri5.py                       # V25 TRI5 child-safeguarding advisory gate
├── test_v25_tri5.py, test_v25_tri5_integration.py
├── synth_shai_doctor/                # AAA Doctor V1 (simulation only, not a medical device)
├── test_synth_shai_doctor.py
├── super_tool_v1.py                  # Super Tool V1 offline ASK / CHECK / BUILD starter
├── test_super_tool_v1.py
│
├── core/, financial/                 # Package groundwork / future modules
└── docs/
    ├── MANIAC_SUPERVISOR.md          # MANIAC + USHAI plain-English guide
    ├── V25_TRI5.md                   # V25 TRI5 guide
    ├── SUPER_TOOL_V1.md              # Super Tool V1 guide
    ├── SHAI_DIGITAL_TWIN.md          # SHAI twin + ELO-ECTRIC (illustrative, not hardware-ready)
    ├── V31_BRIDGE_README.md          # Bridge usage and security boundaries
    ├── V31_RELEASE_VERIFICATION.md   # Release evidence matrix
    ├── PUBLIC_BETA.md                # Public research-beta notes
    └── BUILD_STATUS.md               # Milestones and next step
```

This tree shows `main`. Nothing in it is production-ready.

## 8. Running the verified-scope Python prototype

On a working copy, use Python 3.11 and an isolated environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m unittest discover -v
python3 -m maniac.simulation
python3 shai_finance.py
```

You can also run the financial tests directly:

```bash
python3 -m unittest -v test_shai_finance.py
```

The V3.1 tests run with the commands above (or directly with `python3 -m unittest -v test_verification_v3_1.py`). Installation uses the committed wheel-only hash lock. CI separately checks current dependency advisories and redacted reachable-history secrets. No real-world connections are needed by the offline prototype itself. See the [release/security checklist](docs/RELEASE_SECURITY_CHECKLIST.md) for exact evidence and remaining owner/independent-review tasks.

The main loop defaults to an in-memory audit. Optional `audit_path="audit.sqlite"` stores a verified local SQLite chain;
`audit_expected_head` checks an independently retained checkpoint on reopen. Optional `safety_signals` connects V25 TRI5
before any human decision. See the [integrated synthetic example and persistence limits](docs/MANIAC_SUPERVISOR.md#optional-local-audit-persistence).
Persistence may retain caller-supplied operator identifiers and reasons, so use synthetic data in demos. Audit failure
keeps the loop in HOLD; hash checks do not authenticate a history or prove that a shortened history is complete.

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
- Improve test coverage reporting and keep the hash-locked dependency set and advisory checks current.
- Separate future robot, finance and infrastructure validation plans into self-contained modules with explicit safety cases.
- Obtain independent domain-specific review before any live financial, physical, or public-facing high-risk feature.

## 10. Security, privacy, and responsible contributions

Never commit passwords, access tokens, private keys, personal banking data, sensitive personal records, or information belonging to children. Use synthetic fixtures wherever possible. Keep logs minimal and scoped; obtain meaningful consent before using real records. Keep physical actuation and external network side effects disabled in local demos.

Release/security evidence and owner actions are tracked in [docs/RELEASE_SECURITY_CHECKLIST.md](docs/RELEASE_SECURITY_CHECKLIST.md); the [trust-boundary review](docs/TRUST_BOUNDARIES.md) distinguishes checked evidence from caller assertions.

For contributions, propose a small, inspectable change with its motivation, a reproducible test, negative/failure cases, risks, and rollback plan. Submit by pull request; human review is required before merge. Report security vulnerabilities privately rather than publishing working exploit secrets in issues.

## 11. Project philosophy

**Kwa'kah Tuuwanasavi** — a project expression of balance and connection.

**Connection over power. Rejuvenation always.** Rejuvenation can mean helping a person, system, community or ecosystem continue being itself, on its own terms.

SYNTH_SHAI is intended as a careful body of ongoing work: teachable, corrigible, humble about uncertainty, and accountable to people. Its value will come from transparent evidence and responsible application — not from treating names, symbolic codes or simulated outputs as proof of extraordinary capability.

---

**Project stewardship:** Human-led SYNTH_SHAI research.  
**Last documentation review:** 27 October 2026 (PR #48 evidence reconciliation).  
**Status:** Offline prototypes + active research; real-world high-risk actions remain `144 HOLD`.

## License

SYNTH_SHAI is released under the [MIT License](LICENSE). Copyright (c) 2026 Mitch Trimble.
