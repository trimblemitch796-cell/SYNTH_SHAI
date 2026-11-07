# SYNTH_SHAI Android Google identity — Credential Manager / HTTPS contract v0.1

**Status: DESIGN PROPOSAL FOR INDEPENDENT REVIEW — 144 HOLD.**
**Date:** 2026-11-08. **Base:** main @ `21f25733f65b23338140e1e40c69c0fc4e739f24`.
**Scope:** document-only; no new runtime code, permission, OAuth configuration, account activity, network call, public endpoint, signing key, deployment, APK, or authorization to enable online chat.

## 111000 — Evidence and architectural choice

Choose **native Android Credential Manager → Google ID token → authenticated HTTPS backend exchange → separate Ed25519-signed SHAI session** for a *future* bounded chat-only pilot. This is the **Google ID-token path**, not the existing Android Authorization Code + PKCE preflight and not the browser/BFF `__Host-SHAI-Login` cookie path. They are separate alternatives and MUST NOT be silently composed.

Existing material:
- `android-app/app` is an offline Kotlin/Compose application `org.tuuwanasavi.synthshai`, version 0.2.3.1, SDK 26–35; manifest has no INTERNET permission, no credential UI or network transport.
- `android-app/app/src/main/java/org/tuuwanasavi/synthshai/auth/AndroidPkcePreflight.kt` implements offline PKCE/redirect checks, **not** Credential Manager.
- Main's `SYNTH_SHAI_staging_gateway/pilot_security.py` verifies pinned, short-lived (<=900s) EdDSA SHAI JWTs. The private signing key and issuer service do **not** exist in the implementation.
- Draft PRs #98 (synthetic Google RS256 verification), #100 (atomic one-use nonce/challenge), #101 (synthetic/key-cache rotation) and #102 (browser-cookie session binding) are *not merged*. The #102 browser-cookie binding is NOT native Android authentication. PR #99 is a separate offline preview/loopback fixture, not live Google identity.
- Existing gateway is localhost-only and its pilot switch is OFF. No public HTTPS service or live identity evidence has been established.

Reference guidance:
- Android: https://developer.android.com/identity/sign-in/credential-manager-siwg-implementation
- Google OIDC: https://developers.google.com/identity/openid-connect/openid-connect
- Google backend ID-token guidance: https://developers.google.com/identity/sign-in/android/backend-auth

**Trust boundary:** the Android application and all request body fields are untrusted. Only the server is authoritative for nonce, expected audience/authorized-party policy, Google signing keys, session issuance, quota, revocation and authorization. The app package/signing certificate must be registered for Google identity configuration, but this is not cryptographic proof that every HTTP request came from an untampered app. Do not treat email/profile claims as authorization; key accounts by verified Google `sub` (or a server-side internal ID mapped from it).

## 333000 — Proposed native Android behavior (NOT IMPLEMENTED)

1. User explicitly taps **Sign in with Google**. Offline lessons remain accessible without a Google login; no automatic sign-in, data upload or new permission in this phase.
2. App starts a new one-use HTTPS preauthentication transaction at `POST /auth/challenge`. The response contains server-created `challenge_id`, a 256-bit-or-better unpredictable `nonce`, and a **separate**, unpredictable, server-issued `completion_token` (opaque bearer proof of possession of this pending transaction). Hold all three **in process memory only**, never in logs, URLs, backups or persistent preferences; discard on cancel, expiration, process restart or sign-out. At most one pending attempt per app login UI.
3. Credential Manager is invoked from Activity context with Google's `GetSignInWithGoogleOption` (explicit button path), `serverClientId =` operator-registered **Web OAuth client ID**, and `nonce =` the exact server-issued nonce. Optionally evaluate `GetGoogleIdOption` for a subsequent returning-user experience *only after* review. `GoogleIdTokenCredential` must be parsed through Google's supported library, with cancellation/no credential errors handled without fallback to custom WebView.
4. App sends the resulting **ID token only to** `POST /auth/google`, with its `challenge_id` and `completion_token`, over verified TLS. No Google token, authorization code, PKCE verifier or refresh token is submitted to `POST /chat`.
5. If the server responds with a SHAI access token, app keeps the short-lived SHAI credential in volatile memory only for initial staging; this design does **not** authorize refresh/persistent login. Re-authenticate after expiry. Use `Authorization: Bearer <SHAI-access-token>` for chat only after independent approval of the complete service; do not add autonomous tools.
6. Logout revokes the active SHAI `jti` server-side, clears app-memory tokens, and calls Credential Manager `clearCredentialState` for local sign-out context. Do not imply this signs a user out of their Google account. Switching accounts always requires a fresh challenge and discards pending state.

**Design limits:** This is a bearer `completion_token` native-mobile approach rather than a cookie. TLS, short expiry, no third-party logging, server-issued token digest, atomic consumption, limited attempts and no account inference are necessary. An attacker who obtains that bearer during its validity could claim the pending transaction; do NOT call it hardware/device-bound authentication. A future hardware-backed proof-of-possession or app-integrity requirement is a separate reviewed enhancement.

## HTTPS request/response *proposal* — none of these routes exist

JSON UTF-8; POST only; `Content-Type: application/json`; `Cache-Control: no-store`; strict bounded body sizes; no query-string credentials; HTTPS only, approved host, trusted proxy, no redirects. All values below are **illustrative placeholders**, not real credentials.

### POST /auth/challenge (unauthenticated, heavily rate-limited)

Request:
```json
{"flow":"google-id-token-v1","platform":"android"}
```

Response `201`:
```json
{"challenge_id":"<opaque random id>","nonce":"<random base64url nonce>","completion_token":"<separate random bearer secret>","expires_in":300}
```

Server creates transaction, nonce and completion bearer with independent CSPRNG values, minimum 256 bits each; stores digests of bearer and nonce, creation time, absolute deadline and single-use state in a trusted **atomic shared store**. Only the API can create trusted binding state; never accept a client-computed `binding_hash`. Concurrency, clock rollback, missing/corrupt DB, expired state and second consumption deny. Return no account identity. Restrict challenge creation, completion attempts and IP/device abuse patterns without trusting user-supplied identity.

### POST /auth/google (unauthenticated, one-use exchange)

Request:
```json
{"challenge_id":"<id from challenge>","completion_token":"<secret from challenge>","google_id_token":"<Google ID token from Credential Manager>"}
```

Server flow: validate strict schema/limits and trusted channel; look up transaction and compare completion-token digest (constant-time); atomically **consume the attempt before** cryptographic verification and never restore it following any failure; obtain the server-stored expected nonce and pinned Google Web client ID; verify RS256 Google ID-token signature using **server-trusted, fresh JWKS** (never client-supplied keys or JWT-header URLs), issuer, audience, allowed `azp` (when applicable), `exp`, `iat`, expected nonce and acceptable `sub`. Reject unknown/stale signing keys without request-driven arbitrary key fetching; handle provider outage fail-closed. Only verified `sub` can be mapped to an internal subject.

After checks pass and all fail-closed stores/limits are available, the separately reviewed **server-only** Ed25519 issuer signs a SHAI JWT with exactly the existing gateway's accepted claims `iss,aud,sub,jti,iat,nbf,exp`, header `{"alg":"EdDSA","typ":"JWT"}`, absolute TTL <=900 seconds, unique `jti`, trusted signer custody, and a subject compatible with the gateway allowlist. Google email is never a `sub` substitute. A real issuance service, private-key custody, rotation, and logout/revocation wiring remain unimplemented.

Response `200`, **only after** the independent review and successful live authentication:
```json
{"token_type":"Bearer","access_token":"<SHAI signed session JWT>","expires_in":900}
```

All failures use **generic** error bodies; never reflect raw token, account email, nonce, signature, signing key or user existence. Illustrative result classes: `400` malformed input, `401` verification/invalid/replayed/expired attempt, `429` throttled, `503` trusted service/store/JWKS unavailable. Minimize timing or error-oracle differences. No refresh flow in v0.1.

### POST /auth/logout (SHAI bearer required)

Use the **SHAI session**, not the Google ID token. Verify it, atomically insert its `jti` into the trusted revocation store, then return `204` (no body). Fail closed on unavailable store rather than claiming logout is complete; app still clears local credentials and displays an honest warning if server-side revocation was not confirmed. Existing `pilot_security.revoke_session` is operator-only; a reviewed authenticated HTTP adapter is a **gap**, not complete functionality. Expired sessions still need policy-defined revocation behavior. Multi-device account-wide sign-out is explicitly out of scope.

## 555000 — Acceptance / adversarial verification matrix

All listed checks are **PENDING**, not claims that the new flow was tested:

| ID | Offline gate before any live review | Expected |
| --- | --- | --- |
| A01 | Challenge uses server-generated independent entropy and 300s bounded TTL | PASS only if entropy and expiry verified |
| A02 | Client-supplied binding hash, nonce substitution or chosen challenge ID | DENY |
| A03 | Duplicate finish, wrong bearer, concurrent completions, expiry, clock rollback | DENY and one-use consumption |
| A04 | Malformed/oversize JSON, duplicate keys, missing fields, invalid encodings | DENY |
| A05 | Google token wrong `aud`, `iss`, `azp`, `exp`, `iat`, `nonce` or format | DENY |
| A06 | Forged Google RS256, wrong algorithm, JWT-provided `jku`/`jwk`, unknown `kid` | DENY |
| A07 | JWKS expired, rotation, fetch failure, wrong endpoint, redirects, untrusted TLS | DENY / refresh only by reviewed policy |
| A08 | Successful synthetic validation issues only exact-profile <=900s SHAI session | PASS in offline mock; NOT live login |
| A09 | Google ID token, OAuth code, PKCE value and symbolic approval used at `/chat` | DENY |
| A10 | Forged/self-signed/expired/revoked SHAI token; mismatched issuer/audience | DENY |
| A11 | Logout revokes exact `jti`; database outage cannot report successful server revocation | DENY / honest error |
| A12 | Cancel, rotate Activity, restart, sign out or account switch mid-flow | No cached completion secret; fresh login |
| A13 | No INTERNET permission, online calls, embedded key, or new login side effect in offline APK | Existing behavior unchanged |
| A14 | TLS proxy, hostname verification, HSTS where applicable, auth header redaction, request limits | Independent review required |
| A15 | Tests with changed Google keys, real Play Services, real OAuth client and physical device | PENDING until explicitly approved |
| A16 | Quota/revocation remains correct on restart, concurrent hosts and service shutdown | PENDING independent evidence |

Do not equate tests using temporary RSA keys and local SQLite with real Google identity authentication. Test the exact Android signing variant: CI-generated debug APK signatures may differ from local or release signing fingerprints. Verify `org.tuuwanasavi.synthshai` signing lineage, Google Cloud Android OAuth client association and the corresponding Web client ID **before** invoking a real login. Client IDs are public configuration; client secrets and server signing/private keys must **never** be in Android source, logs or chat.

## 888000 — Build/review sequence and decisions still pending

1. **Documentation decision (this PR only):** review this Credential Manager ID-token contract, threat model and the alternative PKCE/browser paths; record reviewer objections before code.
2. **Separate offline implementation PR:** Android UI contract, mocked Credential Manager adapter and cancellation/lifecycle tests, with the existing manifest/installed APK unchanged until an explicitly approved integration step.
3. **Separate offline server PR:** native-server-issued bearer challenge adapter, one-use transactions, Google verifier/JWKS composition, SHAI signer and protected logout; mocked HTTP harness with zero provider calls; review against draft #98–#102 instead of assuming those unmerged changes exist on main.
4. **Independent security review:** authentication bypass, challenge theft/replay, mobile client substitution, trusted proxy/TLS, signing-key custody, cross-instance shared storage, time, expiry, revocation, budgeting and incident response.
5. **Explicit new human approval only after evidence:** Google Cloud OAuth setup, actual Google test account, signed Android package configuration, external HTTPS staging endpoint, physical device login, and any chat/API spending. No action in this document grants such approval.

**Decision gates / unanswered:** Which Google Cloud project and signing-certificate lineage; operator-controlled HTTPS host; durable cross-instance transaction and revocation store; independently managed signing key/KMS; audience/azp acceptance matrix; session-renewal strategy (none in v0.1); security reviewer identity; bounded pilot shutdown and cost budget. These are OPEN, not assumptions that can be filled with fake values.

**444000 = human authority; 144 HOLD = default.** This documentation PR must remain draft: NO merge, deployment, Google login, network permission, live token, cloud configuration, API spend, or tool execution authorized.
