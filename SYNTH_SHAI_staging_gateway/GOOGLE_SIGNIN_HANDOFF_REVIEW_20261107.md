# Google sign-in for SYNTH_SHAI — offline identity verification preflight

**State: 144 HOLD. Separate review branch. No Google account, OAuth client, real public keys, identity provider, login screen, runtime /exchange endpoint, SHAI session signing, API call or Render service created.**

## 111000 — Evidence and architecture selection

Google's Android Credential Manager supplies a Google ID token using a **server client ID** and can bind a supplied nonce. The backend must verify Google's signature and issuer, the correct audience and expiry using Google's rotating public keys. The stable account key is Google's opaque **sub** rather than an email address.

Sources:
- https://developers.google.com/identity/android-credential-manager/android/reference/com/google/android/libraries/identity/googleid/GetGoogleIdOption
- https://developers.google.com/identity/openid-connect/openid-connect
- https://developers.google.com/identity/sign-in/android/backend-auth
- https://developers.google.com/identity/gsi/web/guides/verify-google-id-token

The existing Android PKCE S256 class represents a *different* future Authorization Code flow. Do not silently combine the PKCE callback with Credential Manager's ID-token flow or claim that either currently produces SHAI sessions. Choose and independently review ONE real login architecture before adding UI/network access.

## 333000 — Defined offline trust boundary

Added google_oidc_preflight.verify_google_id_token(): only accepts a bounded, synthetically signed RS256 ID-token-shaped fixture when given (a) a trusted server-configured Google **web client ID**, (b) a fresh server-owned expected nonce, (c) server-selected trusted RSA public keys keyed by kid, and (d) an explicit authorized-party pin if required. It checks strict header shape, canonical base64url, signature, issuer, audience, nonce, sub, iat, exp, optional nbf and azp. It returns *only* a VerifiedGoogleSubject with opaque sub.

It NEVER downloads Google's keys, trusts JWK or jku from a token, accepts credentials from an Android client as verification keys, mints a SHAI session, creates a HTTP endpoint, or invokes the OpenAI provider. Google ID tokens remain incompatible with the existing EdDSA SHAI gateway bearer JWT. Tests use fresh synthetic RSA keys, not Google's actual keys. Rejecting an invalid signature is not sufficient evidence of correctly configured Google trust.

## 555000 — Offline tests

Run: python -m unittest -v SYNTH_SHAI_staging_gateway.test_google_oidc_preflight
Then: python -m unittest discover -v

Negative cases include wrong issuer/audience/nonce/azp, expiry and clock errors, alg confusion, forged signatures, unknown kid, untrusted JWKS URLs, duplicate JSON fields, invalid subjects, untrusted email and Google-token-as-SHAI-session rejection. No real sign-in or network call occurs. No Android APK behaviour changes.

## 444000 — Work remaining and deployment gate

1. Create and review a Google Cloud project with exact Android package **and signing certificate fingerprints** plus a corresponding web/server OAuth client ID. Never paste credentials into source, chat or Android resources. Debug APK signing identities may differ across runner builds.
2. Decide between Credential Manager + ID-token handoff and OAuth Authorization Code + PKCE; do not mix the two until independently modelled. Establish Android lifecycle, account change/logout, consent handling and system authentication UI.
3. Implement a vetted **server-side Google JWKS resolver/cache with rotation and expiry**, trusted provenance, safe retry/failure behaviour, and offline/real compatibility tests. This module intentionally contains no live Google HTTP requests.
4. Establish a trusted, atomic, shared **one-use nonce/transaction binding** to the initiating session; the pure verifier only compares against a caller-supplied nonce and does not prevent replay across requests.
5. Review a separately secured login/exchange service with anti-replay protection which can mint a <=15-minute Ed25519-signed SHAI session in server-only key custody. Never expose its signing key, OpenAI key, or Render keys in the APK. Google ID tokens **must not** be passed to /chat.
6. Keep the gateway pilot default disabled. Validate persistent rate/quotas across replicas, public HTTPS reverse-proxy configuration, logged-out revocation, finite API budgeting, and independently scheduled Render shutdown before asking for any limited live test.

**No merge or deployment authorised by this review alone. No existing code or permissions changed. 144 HOLD applies throughout.**
