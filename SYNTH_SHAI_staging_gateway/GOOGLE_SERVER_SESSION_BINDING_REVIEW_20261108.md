# Server-owned login transaction binding — offline research

**144 HOLD.** A stateful server-side **pre-authentication browser cookie** was implemented, but no Google account has signed in and no SHAI login service is hosted. This does **not** yet solve a native Android Credential Manager session handoff.

## What was implemented

The server generates a unique 256-bit opaque cookie, persists only its SHA-256 digest and timestamps in an operator-provisioned SQLite database, and issues the __Host-SHAI-Login cookie with Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=300 and no Domain. The browser/client never chooses or transmits a binding hash. A request supplies only a cookie; server state proves the session was issued. Strict origin matching is required by the API (the expected origin must be independently configured on the server).

On login begin, a verified session is marked "started" atomically in trusted SQLite; only one challenge may be issued for that session. The challenge binding hash is derived server-side from the verified cookie digest, not from any client-supplied "binding" parameter. On completion, the session row is *deleted before* consuming the one-use challenge and verifying a synthetic Google token; even invalid callbacks cannot reuse that cookie. Explicit revocation/logout invalidates the session.

The existing **Google login one-use challenge** and **Google ID-token synthetic verifier** remain in the stack. The Google token is **never** treated as a SHAI /chat bearer token. No SHAI session issuer or signing key was created.

## Limitations / security review required before live use

- Browser cookie is a bearer credential. A stolen cookie can impersonate the preauth session until expiry; strict TLS/HSTS, reverse-proxy Host checks, CSRF/Origin validation and rate limiting require a separately reviewed real HTTPS handler. Exact Origin comparison in a pure module is not evidence that a deployed reverse proxy is correctly configured.
- Cookie session is for a browser/BFF design and **does not automatically bind Android Credential Manager's native ID token handoff**. Decide one architecture and verify the Android package/signing certificate and Google OAuth client IDs before any on-device login.
- SQLite atomicity assumes one trusted shared database file. No durability across Render replicas, backups, tampering, file permissions, trusted time, failure recovery or identity-provider outages is established by these tests.
- No real Google public keys are retrieved; the prior PR #101 cache has an optional pinned HTTPS fetcher, never invoked by /chat. A reviewed Google JWKS refresh and policy would still be required for real use.
- No account identity, Ed25519 SHAI session signing, credential exchange endpoint, secure token storage or logout across devices is supplied. Only synthetically signed Google tokens are used in the tests.
- No Android permission changes, deployment, secrets, Render actions, or API credit use.

## Tests

python -m unittest -v SYNTH_SHAI_staging_gateway.test_google_server_binding
python -m unittest discover -v

16 tests cover secure cookie attributes, first-use authorization, forced logout, expiry, wrong Origin/duplicate cookies, cross-session challenge theft, forged cookie rejection, concurrent starts/callbacks, malformed callback token, and fail-closed missing state. These project-maintained tests require independent review.

**Code-only draft, not approved to merge or deploy. 144 HOLD remains active.**
