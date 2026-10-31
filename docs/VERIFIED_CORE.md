# SYNTH_SHAI — Verified Core Inventory (31 October 2026)

**Scope:** This is a conservative inventory of code whose associated automated
tests ran successfully on the PR #61 candidate. It is not a claim that every
module is production ready, or that all code has undergone independent review.
The repository contains both working offline prototypes and unfinished designs.

**V2–V4 security research status correction (1 November 2026):** Signed-administrator verification, default-deny dispatch, separate-process workers and Linux resource-limit mechanisms are **offline research prototypes**. They do not by themselves demonstrate trusted operator identity, filesystem or network isolation, a complete security sandbox, or permission for live execution. Project-maintained tests are not an independent audit. Consequential use remains **`144 HOLD`** until independent review and explicit human authorization. Implementation, testing, independent validation and deployment authorization must be tracked separately.

## Keep: demonstrated offline components

| Component | Code | Evidence or limitation |
| --- | --- | --- |
| V3.1 signed-evidence verification | `verification_v3_1.py`, `verification_v3.py` | Signature, missing evidence, replay tests; local trust assumptions |
| Offline evidence Safety Lab | `safety_lab_demo.py` | Missing evidence HOLD, valid evidence REVIEW_REQUIRED, replay HOLD |
| Signed approval check | `offline_approval_v1.py` | Exact plan/action binding, expiry, nonce replay; **never executes** |
| Signed administrator revocation | `offline_operator_admin_v2.py` | Signed administrator envelope, replay check; trusted local keys/database |
| MANIAC simulation, monitor and audit | `maniac/` | Synthetic fault-injection, hash-linked local audit, regression coverage |
| Safeguarding review and CATHARSIS | `v25_tri5.py`, `ushai_catharsis.py` | Synthetic advisory checks, no real-world safeguarding guarantees |
| Financial education, power and digital twin | `shai_finance.py`, `shai/` | Tested educational calculations and simulated hardware only |
| Inbound WhatsApp bridge | `whatsapp/` | Local tests; **not** an enabled outbound service |
| Research referee, bridge and doctor | `maniac/synth_shai_referee.py`, `shai_v31_bridge.py`, `synth_shai_doctor/` | Offline/synthetic tests; not independent or clinical certification |

The latest reviewed **PR #61** candidate ran 557 tests on both Python 3.11
(4 skipped) and Python 3.13 (3 skipped), with zero failures. These counts
belong to that specific revision. Re-run on any newer revision before citing
passing CI. See GitHub Actions and the individual test files for detail.

## Keep separate: research, plans and unvalidated claims

- `docs/WHATSAPP_FAST_ACK_SKETCH.md` is a design sketch, **not** a live
  multi-model service. It must not be described as operational.
- `docs/DISAGREEMENT_REFEREE_SPEC.md` is a specification; distinguish it
  from the tested offline referee implementation.
- `docs/MISSION.md` and other architecture documents describe ambitions,
  not implemented external services.
- The Character.AI configuration is external and **not** proof that GitHub
  verification code runs inside Character.AI.
- An authenticated administrator signature is not a production execution
  boundary: trusted host identity provisioning, secure key lifecycle,
  distributed replay/revocation and independent adversarial review remain open.

**No unexplained deletions.** Passing tests justify preserving the modules
until a file-by-file dependency and feature review establishes that a file is
dead, duplicate or broken. Experimental ideas are retained as clearly
labelled research rather than silently discarded.

## Minimal reproducibility

From the repository root using supported Python and pinned dependencies:

```bash
python -m pip install -r requirements.txt
python -m safety_lab_demo
python -m unittest discover -v
python -m maniac.simulation
```

All commands are for an isolated development environment. Avoid private
credentials and live integrations. `144 HOLD` remains the default when
evidence or authorization is incomplete.

## Cleanup policy

1. Keep tested core modules, their tests, dependency locks, security docs
   and workflow configurations.
2. Keep design-only material labelled as research; do not advertise it as a
   working feature or silently delete intellectual property.
3. Delete or archive a source file only after proving that it is unused,
   confirming tests remain green and reviewing the removal with the owner.
4. Do not equate a passing unit test with independent validation or
   production certification.
