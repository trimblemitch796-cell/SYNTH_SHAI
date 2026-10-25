# SYNTH_SHAI / USHAI — AAA Doctor V1

**Status: simulation-only / NOT FOR CLINICAL USE / unvalidated prototype.**

AAA has two separate meanings here:
- **Adaptive Analysis Assistant**: project decision-support architecture.
- **Abdominal Aortic Aneurysm**: vascular condition handled by the specialised safety rules.
- **AAA Emergency Code**: *project-specific* escalation flag; **not** an official hospital code or clinical emergency standard.

## The three modules
1. Medical AAA: conservative recognition of certain danger signs; no diagnosis, imaging interpretation or treatment advice.
2. SYNTH_SHAI Doctor Code: typed consent-based case, transparent rule results, no hidden clinical inference or autonomous action.
3. AAA Emergency Code: escalation flag with Australian 000 instruction, no automated calls or dispatch.

## Ethics and authority
`144 HOLD` prevents ordinary processing without consent. Emergency information is still returned in an emergency even without consent. `444000` denotes human project approval / review requirement, **not** clinical verification. `111000` learning is **disabled**; no case-based adaptation or patient records. No uploads, microphones, cameras, biometrics or remote access. This package does not connect to real patient information.

## Synthetic data only
Until external clinical review, every `Case` must use **synthetic data only**:
- `case_id` must start with `SYNTHETIC-`, for example `SYNTHETIC-001`.
- `notes` must be empty, because no free text is accepted.

Anything else raises `ValueError`. `consent` and every symptom field must be a real `True`/`False`, and `known_aaa` must be `True`, `False` or `None`.
Anything else, for example `consent='no'`, raises `TypeError`, so a text value can never bypass `144 HOLD`.

## Run locally (from the repository root)
```bash
python3 -m unittest -v test_synth_shai_doctor
python3 -m synth_shai_doctor.core
```

## Limitations
- Rule coverage is deliberately narrow; no negative result is proof of safety.
- Free-text notes are not used for automated interpretation.
- No diagnostic validation, regulatory assessment, field studies, clinician sign-off or integration testing.
- Must not guide unsupervised clinical decisions or replace emergency services.
- If someone may have a medical emergency in Australia, call **000**; do not use this code to decide whether to seek help.

## Clinical sources (checked 26 Oct 2026)
- Queensland Health, Aortic Aneurysm CPC: https://www.health.qld.gov.au/cpc/vascular/aortic-aneurysm
- Healthdirect, calling 000: https://www.healthdirect.gov.au/healthcare-and-services/emergency-and-urgent-care/calling-triple-zero
- Healthdirect, abdominal pain emergencies: https://www.healthdirect.gov.au/conditions/gastro-intestinal-illnesses/what-causes-abdominal-pain

## Next approval gate
External clinical review, broadened hazard analysis, tests for missed escalation, regulatory/privacy review, locked change management, and independent validation **before** any real-world clinical use.
