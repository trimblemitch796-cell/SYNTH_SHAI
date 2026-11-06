# SYNTH_SHAI Android identity handoff — offline review V0.1

**State: 144 HOLD.** This file defines a security boundary for future Android authentication. It is NOT an identity provider, working login, authorised public gateway, or a deployment plan.

## 111000 — Existing evidence

The gateway already verifies an exact-profile, short-lived (<=15 min) Ed25519-signed bearer session using a **server-pinned public key**, issuer, audience, time fields, subject and unique session identifier. A separate trusted issuer is required. The mobile client cannot create a valid session on its own. The existing quota/revocation database must be trusted and persistent, not inside the Android app. API credentials are read from the server environment only.

## 333000 — Defined mobile sign-in boundary

A future Android login must use an independently selected and reviewed OpenID Connect/OAuth provider with **Authorization Code + PKCE (S256)** in a system browser, a verified redirect binding, a fresh high-entropy state and OIDC nonce, and secure token storage appropriate to Android. The Android APK receives **no client secret, service signing key, Render API key, or OPENAI_API_KEY**.

An OIDC ID token, OAuth authorization code, refresh token, or self-signed JWT must NOT be accepted as a SHAI gateway session by default. An independently secured backend/issuer must establish the authenticated human principal and issue a **distinct, narrowly audience-bound, <=15-minute SHAI session** that fits the pinned verifier profile, or the verifier must be replaced by a separately reviewed standards-compliant bearer resource-server design. Do not silently mix these architectures.

The backend's existing session validation is NOT proof that the Android PKCE exchange, login/consent UI, token issuer, signing-key custody, or logout/revocation integration exists. All of these remain unimplemented.

## 555000 — Offline evidence and test scope

Run:
    python -m unittest -v SYNTH_SHAI_staging_gateway.test_android_identity_boundary
    python -m unittest discover -v

The new bounded cases check: a locally generated trusted-signature fixture is accepted; an attacker/self-signed key or a key embedded in untrusted header is rejected; opaque OAuth codes, symbolic approval strings and unrelated provider tokens are not trusted sessions; extra ID-token style claims are rejected; missing trusted configuration, expiry longer than 15 minutes, and revoked sessions fail closed. These use synthetic identities, fake keys and temporary SQLite files **without network or paid API calls**.

The tests do **not** establish a working OIDC provider, verified PKCE, Android security, browser redirection correctness, interoperability, hosted TLS, multi-instance quota isolation or independent assurance.

## 444000 — Human/independent gate before any live pilot

A named human operator must choose the issuer and Android package/redirect design, and an independent technical reviewer must inspect the login flow, issuer key rotation, signature verification, account switching, token lifecycle and revocation. Verify a trusted, durable, shared quota/revocation store across restarts/workers and a separately scheduled and tested hosting shutdown; provider request ceilings are not dollar-spend guarantees. Keep all action, messaging, tool use, deployment and financial privileges denied.

The staging branch remains isolated and **draft PR #92 must not be merged or deployed** on the strength of project-authored offline checks alone. No Render service exists or is created by this work. 144 HOLD continues.
