# SYNTH_SHAI — Cloud Run Google login backend preparation (2026-11-08)

**DRAFT / 144 HOLD — code and planning only. No deployment, public login,
merge, billable resource, Google user authentication, or SHAI actions authorised.**

## Evidence as of 8 November 2026

- Google Cloud Console read-only inspection of project `synth-shai-staging`:
  **Cloud Run Services was empty.** No service hostname or HTTPS origin exists.
- Android draft [PR #104](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/104)
  builds `org.tuuwanasavi.synthshai.staging`. The Web OAuth client ID is
  configured, but the staging origin is empty and sign-in stays disabled.
- The operator confirmed creating an Android OAuth registration for this exact
  package and for SHA-1 `2F:DB:92:30:6E:C0:90:FD:6E:2D:6F:BA:CE:CF:4C:FF:A0:F6:FA:9F`.
  The fingerprint describes the **particular previously inspected staging APK**;
  ephemeral CI debug certificates may differ on future builds. Google acceptance
  and a physical-device login have **not** been verified.
- This branch is stacked on draft backend [PR #105](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/105).
  That PR implements an **in-process** `NativeExchange` WSGI contract with synthetic
  Google signing keys and a temporary SQLite fixture, not a hosted identity service.

## Blockers that must be resolved before any real Cloud Run connection

1. **TLS/WSGI trust boundary — BLOCKED.** Cloud Run terminates public HTTPS
   upstream of the container. `NativeExchange.dispatch()` currently checks
   `wsgi.url_scheme == "https"`. A typical direct Cloud Run WSGI request reaches
   the container as HTTP and is therefore rejected. Never fix this by blindly
   trusting client-supplied `X-Forwarded-Proto`, `Host`, or `X-Forwarded-For`.
   Design and independently test a trusted Cloud Run/ingress-aware adapter that
   identifies the expected external scheme and **exact host** without giving
   arbitrary client headers authority. Until then, **do not expose the handler**.
2. **Shared atomic state — BLOCKED.** The challenge, revocation and quota
   code assumes one durable SQLite file. Cloud Run instance storage is not a
   trustworthy shared transaction/revocation database across instances,
   restarts or revisions. Select and test an operator-owned, durable shared
   transactional store before login; verify one-time consumption, logout and
   global quotas under concurrent replicas.
3. **Provider trust — BLOCKED.** Provision a trusted background refresh path for
   Google's pinned HTTPS JWKS (expiry, rotation and outage fail closed), using
   reviewed egress controls. The in-process synthetic cache is not evidence
   of live provider verification. Enforce issuer, exact Web Client `aud`,
   native Android `azp` policy, nonce, expiration and Google `sub` allowlist.
4. **Signer / session custody — BLOCKED.** No trusted production operator
   signer, matching verifier, signer rotation or shared revocation service is
   configured. Keys must remain server-side in approved protected infrastructure
   (for example restricted Secret Manager / KMS), never the APK or git history.
   Do not issue a SHAI session from a token without a verified identity.
5. **Exposure, abuse, cost — BLOCKED.** A Google ID token intended for the Android
   app is **not** a Cloud Run IAM Invoker token. A private IAM-only service will
   not automatically be callable from that Android flow. Any publicly reachable
   `/auth/challenge` endpoint needs explicit design approval: no `/chat`
   route, strict rate limits with trusted client-IP derivation, request size and
   timeout caps, account allowlist, audit redaction, bounded scaling and cost.
   Do not set unauthenticated access or enable an external ingress as a shortcut.
6. **Service lifecycle — BLOCKED.** No reviewed WSGI/ASGI entrypoint, container
   image, pinned runtime, startup preflight, restricted service account, HTTPS
   endpoint, health/readiness contract or secure deployment pipeline exists.
   No secrets or credentials are to be placed in source or GitHub artifacts.

## Non-deployment review sequence

1. **Current offline checkpoint:** run
   `python -m unittest SYNTH_SHAI_staging_gateway.test_native_google_exchange`
   and inspect exact-head CI. New regression checks assert that an untrusted
   `X-Forwarded-Proto: https` cannot turn an HTTP WSGI request into an accepted
   challenge and that unknown Host, empty Google JWKS, missing store and broken
   limiter deny access. These tests do not test Cloud Run itself.
2. Independently review the network/identity threat model and agree on a
   trusted Cloud Run transport boundary. Obtain an explicit choice for the
   multi-instance durable transaction/revocation store and revocable signer.
3. Implement a deployable **separate** staging identity service with startup
   fail-closed dependency checks and no AI/tool execution routes; exercise
   failure cases in a contained non-public environment before a cloud change.
4. Require a separate **444000 human approval** specifying the Google Cloud
   project, region, expected billing scope, host, IAM/ingress, allowed Google
   subjects and testing window before creating any cloud resource.
5. After approved provision and independent review, verify the exact installed
   signed APK against its registered Android OAuth package/SHA-1, then build
   an APK whose **reviewed HTTPS origin** is supplied explicitly. Test one
   user-initiated sign-in and immediate logout, replay failure, unauthorized
   account rejection, invalid Google token, session revocation, logs, key outage,
   concurrency and budget behavior. Record evidence; do not equate CI with
   independent authentication verification.

## What has *not* happened

No Cloud Run container has been created, no HTTPS domain has been selected, no
new APK has been built, no live Google account has signed in, and no API or
autonomous execution has been enabled. The project-wide **144 HOLD remains**.

## Sources

- Google Cloud Run public HTTPS termination and external proxy considerations:
  https://docs.cloud.google.com/run/docs/triggering/https-request
- Google Cloud Run ingress and service identity:
  https://docs.cloud.google.com/run/docs/securing/ingress
  https://docs.cloud.google.com/run/docs/securing/security
- Cloud Run Secret Manager guidance:
  https://docs.cloud.google.com/run/docs/configuring/services/secrets
- Cloud Run concurrency, instance and cost controls:
  https://docs.cloud.google.com/run/docs/configuring/concurrency

**111000 LEARN → 888000 VERIFY → 444000 HUMAN APPROVAL. 144 HOLD.**
