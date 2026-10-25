# Security Policy — SYNTH_SHAI Research Beta

## Supported scope
SYNTH_SHAI V3.1 is an offline research prototype. Its verification functions and tests are available for study; no production security assurance or operational safety certification is claimed.

## Report privately
Do not publish attack steps, secret material, sensitive records or exploit payloads in public GitHub issues. Use GitHub private vulnerability reporting if enabled by the maintainer; otherwise request a private contact method without disclosing details.

Include version/commit, impact, a minimal sanitized reproduction, and whether real secrets or people may be affected.

## Safety boundaries
- A cryptographically valid report leads only to REVIEW_REQUIRED, never automatic approval.
- Fail closed to 144 HOLD when inputs, signatures, trust anchors, challenges or storage are invalid.
- SQLite challenge tracking is local; it is not global replay protection.
- Source-code review and test execution are not substitutes for independent security and real-world hazard review.
- No unsolicited live system probing, credential testing or social engineering.

Before enabling public visibility, the maintainer should review repository content **and commit history** for secrets and private information. Removing a secret in a later commit does not remove it from history; rotate exposed credentials and clean history appropriately.
