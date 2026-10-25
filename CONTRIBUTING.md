# Contributing to SYNTH_SHAI

Thank you for helping improve this human-led, verification-first research project.

## Contribution scope
We welcome documentation improvements, reproducible offline bug reports, unit tests, threat-model discussions, accessibility feedback and carefully bounded simulation proposals.

Please open an issue before large architecture changes. Keep pull requests small, explain assumptions and test your changes.

## Required safeguards
- Preserve **144 HOLD** for invalid or missing evidence.
- Preserve **444000** as a human review gate; never turn a successful check into autonomous approval.
- No network-enabled agents, payments, physical actuation, surveillance or third-party contact without a separately reviewed project scope.
- Use generated examples and test-only cryptographic keys. Do not post credentials, private records or personally identifying data.
- Mark conjecture, demonstration outputs and independently verified evidence separately.
- Never pressure reviewers to bypass checks due to urgency.

## Local tests

```sh
python -m pip install -r requirements.txt
python -m unittest discover -v
```

Document any tests you could not execute. Do not claim that CI passing proves real-world safety.

## Issue reports
For ordinary bugs include exact reproduction steps, expected behavior, actual behavior, commit SHA and redacted logs.

For vulnerabilities or potential private-data exposure, **do not publish exploit details in issues**. Contact the maintainer privately through an established secure channel. If none is available, request a private reporting channel without exposing details.

A contributor's pull request does not authorize deployment. Maintainers review and approve merges.
