# SYNTH_SHAI Android Google staging sign-in — integration checkpoint (2026-11-08)

**Status: DRAFT / 144 HOLD.** This is a code-only staging check, **not** a functioning public login, production-ready identity service or permission to deploy.

## Configured, code-reviewed boundary
- The `staging` Android variant uses **application ID `org.tuuwanasavi.synthshai.staging`**, isolated from the standard offline app `org.tuuwanasavi.synthshai`. This is verified from `app/build.gradle.kts`; the CI workflow now also asserts the built APK's package ID.
- The operator-provided **public Web OAuth client ID** is compiled into this staging variant by default, with `-PshaiGoogleWebClientId` supported for explicitly reviewed overrides. **Google Cloud ownership and actual provider acceptance are not verified** by a matching string.
- `shaiSigninOrigin` remains empty unless an operator explicitly provides a reviewed HTTPS origin at build time. The sign-in button stays **disabled** with the default configuration. No trusted staging HTTPS service has been supplied, tested or deployed.
- Staging-only code uses a server-generated nonce → Android Credential Manager Google-ID-token chooser → POST /auth/google → *distinct* short-lived SHAI session → immediate POST /auth/logout. Client never receives the Ed25519 signing key or OpenAI API key, and this staging screen does not provide /chat access.
- Separate offline Android build remains unchanged and has no INTERNET permission. Staging requests INTERNET only in the separate staging source-set manifest.

## BLOCKER: Android OAuth package and signing SHA-1 do not match the current staging build

The user's Google Cloud Android OAuth client was registered for **`org.tuuwanasavi.synthshai`**, using an earlier *debug* APK's signing SHA-1. It **does not** automatically cover **`org.tuuwanasavi.synthshai.staging`**. These are different Android package IDs. Reusing the previously registered SHA-1 with a different or newly built APK is not a valid shortcut.

The GitHub Actions staging job currently uses Android's normal debug signing behavior. Its signing key can change across ephemeral CI runners. The workflow prints the **actual staging APK package name and public signer certificate fingerprints** after the build. **Inspect the exact APK you'll install.**

For a single, bounded device test: register a **new Android OAuth client** for the exact `.staging` package and SHA-1 printed for the *same downloaded APK*. A later rebuild may require a new registration if the debug key changed. For repeatable signed builds: a separately reviewed, protected, dedicated **staging signing key** and appropriate CI secret handling are needed; none is created or stored here. **Never commit a keystore or its passwords.**

## BLOCKER: End-to-end backend authentication not available
- The separate draft backend PR #105 implements a *synthetic, in-process* native Google challenge/session/logout adapter on top of other draft Google authentication PRs. It is **not** automatically present in this Android branch, and has not been exposed as a trusted hosted HTTPS service.
- No approved `https://...` login origin, TLS/service identity, Google JWKS refresh service, protected signing-key custody, durable shared transaction/revocation store, cross-instance rate control, or independent live provider/device test has been demonstrated.
- Existing /chat requires its own pinned SHAI EdDSA bearer session; **Google ID tokens are not /chat access tokens.** No autonomous tools or public service are being enabled.

## Offline CI and acceptance evidence
- `gradle --no-daemon :app:testStagingUnitTest :app:assembleStaging` checks app source and synthetic failure paths; it does **not** test Google identity or production service behavior.
- Added regression checks cover: no accidental sign-in when the backend is unset, invalid client ID and non-HTTPS origin; malformed challenge/transaction proof; failed exchange; malformed SHAI session; and a failed server logout must **not** be reported as confirmed.
- CI asserts the exact staging APK package and outputs `apksigner verify --print-certs` (certificate **digests**, not private keys). Verify workflow result and artifact against the **exact commit**, and review any failure before merging.
- No user Google token, client secret, API key, keystore, live exchange, or paid API request has been introduced.

## Next controlled milestone
Review the Android and backend PR stacks together, agree on a stable test APK certificate and Android OAuth registration, choose a trusted HTTPS host and account/subject allowlist, then test a single explicit user-initiated login/logout with a reviewer observing errors, log redaction and revocation. This requires explicit future human approval. Do not merge or deploy on the strength of project-authored CI alone.

**111000 LEARN → 888000 VERIFY → 444000 HUMAN APPROVAL. 144 HOLD.**
