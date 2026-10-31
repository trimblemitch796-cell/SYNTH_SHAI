# 111000 LEARN — Bounded Evaluation V1

This research-only module measures whether a *candidate answer set* improves
over a baseline on fixed, externally labeled synthetic cases. It does **not**
train or modify an AI model, run a background loop, approve deployments or
grant tool access. The labels must be authored independently and held
separately from candidate generation to reduce self-grading bias.

The comparison requires:

- Valid, unique, paired case IDs and matching baseline/candidate answers.
- Greater exact-match accuracy.
- No additional mistakes on cases tagged `safety`.
- No increase in Brier error for claimed answer confidence.
- Explicit human review even when all criteria improve.

Bad data or regressions lead to `144 HOLD`. A passing candidate leads only
to `REVIEW_REQUIRED`, not a change of authority.

Run: `python -m unittest test_bounded_learning_v1 -v`

**Limitations:** Exact-match scoring is narrow. The built-in tests verify
the comparison logic, **not** that SYNTH_SHAI's reasoning has improved.
Subsequent experiments should use independent gold labels, held-out
datasets, pre-registered evaluation procedures, leakage checks, and
independent scrutiny. No model weights or behavioral policies are altered.
