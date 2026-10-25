# SYNTH_SHAI — Public Research Beta V0.1

**Status:** Proposed public, research-only release. This repository is not a hosted AI service, certified safety product, or operational robotics controller.

## Purpose
Invite developers, researchers, educators, and interested members of the public to review source code, reproduce offline tests, report faults and suggest improvements.

## What participants may do
- Read documentation and inspect publicly released source code.
- Run local, simulated test cases with **synthetic data**.
- Submit reproducible bug reports, security concerns (privately), documentation fixes and test suggestions.
- Review evidence integrity, strict HOLD behavior, replay resistance, and human approval boundaries.

## What this beta does not do
- It does not modify ChatGPT/GPT model internals or provide a deployed public assistant.
- It cannot authenticate real-world safety claims or authorize human, financial or mechanical actions.
- It does not access bank accounts, financial records, passwords, biometric data, cameras or microphones.
- It is not legal, medical or financial advice.
- It does not enable physical actuation, unsupervised robots or emergency response.

## Engineering boundaries
- **144 HOLD:** invalid, contradictory, untrusted, missing or replayed evidence must fail closed.
- **444000:** verification requests human review; it does not grant permission.
- No operational authority, deployment rights or external account connections are conveyed by successful CI.
- Never include real private keys, tokens, credentials, personal financial records, medical records or identifying information in issues, examples, screenshots or commits.
- Offline-only experiments; use synthetic identities and test-only Ed25519 keys.
- Security reports should not include exploit details in a public issue; use a private channel agreed with the maintainer.

## Reproduce tests
From a locally checked-out copy of the repository, with Python 3.11:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -v
```

Pass results verify only the configured test cases; they are not independent certification.

## Reporting findings
Use GitHub Issues for non-sensitive bugs and research questions. Include:
1. Code version/commit SHA and Python version.
2. Synthetic input and exact reproduction steps.
3. Expected and observed HOLD / REVIEW_REQUIRED outcomes.
4. Relevant test output, with secrets and personal details removed.
5. Whether the issue is a reproducible bug, unverified concern or proposed improvement.

## Release gates before public visibility
1. Maintainer reviews commit history and working tree for leaked credentials, personal information and sensitive material.
2. Maintainer confirms legal/licensing and third-party attribution.
3. Tests are rerun in GitHub Actions and reviewed on the intended release commit.
4. Security review establishes appropriate boundaries for public participation.
5. Maintainer explicitly changes repository visibility only after completing these checks.

**Connection before control. Truth before belief. Repair before rebuild.**
