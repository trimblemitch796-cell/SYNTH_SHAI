# SYNTH_SHAI Android secure login — PKCE preflight V0.1

**Status: offline research code only. No sign-in UI, internet permission, OAuth client, user account, identity provider, or connection to staging PR #92. 144 HOLD.**

This adds an isolated Kotlin helper in \`app/src/main/java/org/tuuwanasavi/synthshai/auth/AndroidPkcePreflight.kt\` and JVM tests. The existing scripted Android app and its APK behavior are unchanged.

## What this proves, once CI passes

- A fresh 32-byte SecureRandom value produces the PKCE S256 verifier/challenge; independent 32-byte state and nonce values are created for each attempt.
- The callback's exact configured HTTPS authority/path is checked, including rejection of userinfo, fragments, non-HTTPS redirect URLs, mismatched path/host, unexpected query keys, duplicate keys and malformed parameters.
- State comparison is constant-time, attempts expire after 300 seconds, and each callback consumes its pending request even on validation failure; cancellation also clears it.
- A successful callback yields only an **untrusted authorization code plus PKCE verifier/nonce** to be exchanged and validated later. The code is NOT a SHAI session and cannot authorize calls to the /chat backend.
- This design intentionally does not persist state/verifier across app restarts; interruption requires a fresh sign-in, not trusting an orphan callback.

## What is NOT provided

No provider is chosen, registered or trusted. No Android system browser is launched, HTTPS App Links are not registered in the manifest, and no callback activity exists. No request to a token endpoint happens. No ID token signature/issuer/audience/nonce validation or secure account/session storage is implemented. No signed SHAI gateway session is issued or exchanged. Code inspection, these unit tests and an APK build alone are not independent Android authentication security evidence.

The strict two-query-field callback parser is a conservative fixture contract; many real standards-compliant OIDC providers can include an \`iss\` authorization response parameter (RFC 9207), or other provider response fields. **Do not deploy or silently discard these fields.** Reconcile and explicitly test the chosen issuer's actual response format before writing production integration code.

## Next reviewed implementation steps — separate approval required

1. Choose a real OIDC/OAuth authorization server supporting **Authorization Code + PKCE S256**, with a public native-application client registration and user consent. Explicitly evaluate its issuing identity, Android SDK support and signing-key custody.
2. Configure **verified Android HTTPS App Links** under a controlled domain with a matching Digital Asset Links statement and the actual signing certificate. Validate redirect ownership, package signature, state and nonce using a tested system browser integration (ideally a maintained AppAuth-style library rather than hand-writing login HTTP).
3. Verify token issuer, audience, signature, nonce, expiration, authorized party and revocation using a vetted client/issuer exchange. **Never send an arbitrary OIDC ID token, OAuth authorization code, or refresh token directly to SHAI /chat.** The staging gateway only accepts its specific pinned EdDSA short-lived SHAI session profile, which requires a separately reviewed session issuer/exchange or a reviewed standards-based gateway adaptation.
4. Establish trusted session persistence/logout, request limits after restarts/replicas, independent security review, bounded cost controls and explicit owner approval before any live pilot.

## Verification

Run the Android workflow's existing Java 17 + Android SDK 35 tests:
\`cd android-app && gradle --no-daemon :app:testDebugUnitTest :app:assembleDebug\`

The Android manifest stays offline and has no INTERNET/camera/microphone permissions. There are no client secrets or API keys in this branch. This PR should be reviewed *against the existing V0.2.3 Android branch*, not merged to main, and not combined with the separate online gateway without independently reviewed authentication.

**111000 learn → 333000 define → 555000 triangulate → 444000 explicit human authority. 144 HOLD.**
