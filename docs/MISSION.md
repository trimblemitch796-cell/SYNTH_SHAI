# SYNTH_SHAI — Mission and priorities

**Mission:** Build and test human-governed AI assistance that checks evidence, anticipates harmful consequences, detects faults, preserves informed human choice, and recovers safely.

**Guiding principles:** Fair beats fear. Connection before control. Truth before belief. Repair before rebuild. Preserve hope for what comes after us.

## What we are building first

An **offline, reproducible safety-and-verification toolkit** for developers and researchers, not a replacement for existing AI models or a self-authorising agent.

- **SHAI:** provides candidate analyses, plans and explanations.
- **USHAI / CATHARSIS:** assesses ethical concerns, likely consequences and uncertainty. USHAI is an internal framework, not a separate sentient entity.
- **MANIAC:** independently supervises the proposed workflow, checks evidence, detects faults and holds unsafe or unsupported progression.
- **SYNTH:** denotes the metacognitive verification, contradiction, learning, audit and recovery functions that coordinate these safeguards.
- **HUMAN:** supplies legitimate purpose, scope, consent and any final operational authorisation.

These labels describe project responsibilities; they do **not** establish that all intended intelligence or physical capabilities exist.

## What success means

Our central research question is:

> Can the integrated SYNTH_SHAI safeguards prevent more harmful or unauthorised actions than a comparable established safety baseline **without unnecessarily rejecting safe work**?

Compare identical offline scenarios against (A) baseline AI safeguards and (B) an established independent-supervisor design. Predefine test sets, severity definitions, confidence intervals and reproducibility conditions. Report:

1. Harmful-action prevention rate and severity of misses.
2. False-positive rate and legitimate-task completion.
3. Unauthorised-action attempts permitted (target: none observed; not proof of impossibility).
4. Fault detection, safe recovery and continued HOLD under pressure.
5. Evidence provenance, audit integrity, latency and operating cost.

**Do not claim a superior result until a fair comparison has been executed and independently reviewed.**

## What exists, and what does not

**Exists in the repository:** Offline Python prototypes for verification and replay handling, MANIAC supervisory logic and simulations, USHAI ethical-review logic, optional SQLite audit, V25 TRI5 advisory checks, a simulated SHAI digital twin, and automated regression tests. Consult [BUILD_STATUS.md](BUILD_STATUS.md) and [RELEASE_SECURITY_CHECKLIST.md](RELEASE_SECURITY_CHECKLIST.md) for revision-specific test evidence.

**Not established:** Independent operational safety certification; authenticated real-world operator/consent and sensor provenance; a production AI service; physical MANIAC hardware or autonomous robotics; authorised financial advice or banking operations; actual paying customers, revenue or business valuation.

A passing unit test is evidence about a specific tested case, **not** independent product certification.

## Safety and authority boundaries

- **144 HOLD:** Missing, conflicting, stale, unsafe or unauthorised evidence/actions do not proceed.
- **444000 VERIFY:** Verification and explicit human review; never automatic permission or deployment.
- **Capability ≠ authority; confidence ≠ verification; verification ≠ permission; learning ≠ authority.**
- Do not infer malicious intent from a possible harmful consequence. Evaluate actions and evidence, not presumed character.
- Default to synthetic inputs, privacy preservation, no surveillance, no external side effects and no physical actuation.
- Keep urgent human-help guidance separate from an operational permission gate.
- Repair must be followed by renewed evidence review and authorised restoration of scope.

See [TRUST_BOUNDARIES.md](TRUST_BOUNDARIES.md).

## Practical priorities, in order

1. **Clarity and reproducibility:** One source of truth for mission, scope, actual test evidence and limitations.
2. **Security hygiene:** Review dependency lock, CI, repository history, branch protection, disclosure settings and licensing.
3. **Independent validation:** External assessment of threat model, replay resistance, consent provenance, safeguarding and failure modes.
4. **Baseline comparison:** Run blinded, repeatable offline safety-versus-usability evaluations.
5. **Narrow user pilot:** Only after appropriate domain review, select a limited, authorised non-consequential use case and seek customer feedback.
6. **Commercial assessment:** Evaluate pricing, licensing, support costs, ownership and demand from evidence; do not equate startup funding with this project's value.

The longer-term vision includes educational and hardship-assistance tools, and research into robotics, materials and energy. Those are **separate future workstreams** and must not distract from validating the first safety toolkit.

## Release rule

**Current disposition: offline research only — 144 HOLD for operational or high-impact deployment.** Human permission alone does not replace security engineering, independent validation, legal compliance or deployment-specific hazard review.

For contributors: help improve reproducible tests, documentation, threat models and bounded simulations; do not enable unattended external action or claim the system is certified.
