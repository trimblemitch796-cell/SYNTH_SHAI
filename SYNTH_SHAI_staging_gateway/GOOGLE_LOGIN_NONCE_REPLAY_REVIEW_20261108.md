# Google login one-use challenge — offline-only review

**State: 144 HOLD; research code on stacked draft branch. No working login, trusted HTTPS endpoint, Google Credential Manager UI, real Google keys, deployed SHAI session issuer, or paid API calls.**

## 111000 — Existing evidence
PR #98 prepares an offline validator for Google ID-token-shaped RS256 fixtures. By itself it accepts a caller-supplied expected nonce and trusted public keys. Without a server-issued, transaction-bound one-use nonce, that would not establish a safe live login flow. Google ID tokens are never valid SHAI gateway bearer sessions.

## 333000 — Defined trust boundary
The new \`google_login_challenge.py\` simulates operator-provisioned, single-file SQLite login transactions. It generates independent 256-bit random \`transaction_id\` and \`nonce\` values (each 43 characters), stores only the SHA-256 digest of the nonce and a **trusted server-derived session binding hash**, and enforces a fixed 300-second TTL. An atomic \`BEGIN IMMEDIATE\` delete burns the transaction on the first attempted consumption, whether the nonce/binding is correct or invalid. Competing consumers of one transaction cannot both succeed on the same trusted shared database.

The \`verify_and_consume_google_preflight\` function consumes the challenge **before** invoking the synthetic offline Google token verifier. It returns only Google's opaque verified \`sub\` for a matching token and cannot mint a SHAI JWT.

**The trusted binding hash must NOT come directly from a browser- or Android-controlled parameter.** A future backend would need to issue and authenticate an independent, HttpOnly/Secure session cookie or equivalent challenge ownership binding, and protect against CSRF, cross-site replay, fixation, account switching and cross-device replays. Nothing in these files provides such a cookie, HTTP endpoint, Google identity assurance, JWKS retrieval/rotation, quota store, or session signing key.

## 555000 — Bounded offline tests
\`python -m unittest -v SYNTH_SHAI_staging_gateway.test_google_login_challenge\`
\`python -m unittest discover -v\`

Test the first valid use and rejection of replay, wrong nonce and binding, expiration, clock rollback, malformed IDs, missing/uninitialized store, competing threads, and one-use pairing with locally signed synthetic Google tokens. The tests use temporary SQLite stores, fake identities and temporary RSA keys; they cannot establish restart/disk integrity, permissions, durable multi-replica coordination, reliable trusted clocks, browser login safety, or independent review.

## 444000 — Next hold gate
Before any production or even public staging use: choose actual Credential Manager vs OAuth PKCE architecture; create Google client IDs and Android SHA signing binding with the human operator; fetch/cache/rotate *real* Google JWKS through a hardened verifier; create authenticated server-owned challenge binding and session-token exchange, secure Ed25519 signing-key custody, audit logging and revocation; demonstrate process-restart, database tamper/failure and concurrency; independently review and explicitly approve a tightly limited online pilot.

**No merge, Render deployment, Android permission change, external tools or live API operation authorised by this step. 144 HOLD remains unchanged.**
