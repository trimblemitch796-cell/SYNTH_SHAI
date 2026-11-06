# SYNTH_SHAI — isolated staging chat gateway (review only)

**144 HOLD. Code-only merge authorised 7 November 2026; deployment NOT authorised.** This is a narrow proof-of-concept, not a production system, public service, or Android-ready authentication design.

## Boundaries

- POST /chat accepts only a JSON object with the single field "message". No tool calling, shell, file access, autonomous workflows, financial functions, or external action handlers.
- The previous shared gateway token has been replaced by a **fail-closed, offline research validator** for short-lived (at most 15-minute) Ed25519-signed sessions. Trusted server configuration pins `SHAI_SESSION_PUBLIC_KEY_HEX` (public key only), `SHAI_SESSION_ISSUER`, and `SHAI_SESSION_AUDIENCE`. Invalid signature, wrong issuer/audience, expiry, missing config, or malformed token is denied. The client must obtain tokens from a **separately reviewed identity service**; no signing key or static secret is embedded in an APK. The identity provider and Android PKCE sign-in are **not built or configured yet**, so mobile/public use remains HOLD.
- `pilot_security.py` adds an operator-provisioned SQLite revocation and quota ledger, requiring `SHAI_GATEWAY_DB` to be a trusted, existing, persistent absolute path. Atomic reservations cap a pilot at 30 total requests, 10 per user, 6 globally/minute and 3 per user/minute (on a single shared durable SQLite file). Missing or corrupt storage fails closed. These are *request ceilings, not a dollar cap*; persistence across Render restarts or replicas has not been established.
- Reads OPENAI_API_KEY only from the server environment; it is never accepted from incoming HTTP. Missing configuration fails closed.
- Body limit 4,096 bytes, message limit 2,000 characters, single-process rate limit 5 valid requests per minute, upstream request timeout 12 seconds, maximum model output 256 tokens.
- Fixed provider endpoint: https://api.openai.com/v1/responses; no tools parameter. Provider errors are generic; request data and auth headers are not deliberately logged. The provider call uses store: false.
- Binds to 127.0.0.1 ONLY; it cannot serve Render's public ingress as written. No deployment configuration is provided.
- **Pilot switch defaults OFF.** The trusted server operator must explicitly set `SHAI_PILOT_ENABLED=1` and an absolute, future UTC `SHAI_PILOT_DEADLINE_UTC` such as `2026-11-13T07:00:00Z`; the timestamp must be at most seven days away on every request. Invalid, expired, missing, or disabled settings fail closed (`503 pilot_closed`). The absolute cutoff is not extended by application restarts. **This stops new chat requests, NOT hosting billing or active containers.** No pilot should be enabled until the external shutdown and security review are complete.
- `render_sunset.py` is a **dry-run-by-default** operator helper using Render's documented service suspend endpoint. It will not POST unless the deadline has passed and both `--execute` and `SHAI_SUNSET_APPROVED=YES` are present. It requires `SHAI_RENDER_SERVICE_ID` and `SHAI_RENDER_API_KEY` held outside GitHub and the Android APK. This file does **not schedule itself** or prove suspension: an independently configured and tested external scheduler must execute it, retry failures, and verify the service becomes suspended. Any hosting or associated billing must be checked separately.
- A real deployment needs separately reviewed TLS, mobile authentication/issuer setup, durable cross-instance abuse/rate controls, credential rotation, incident response, provider-side budgeting, tested external scheduler, safe shutdown, logging, load limits and code isolation. This gateway is NOT wired into the existing SHAI/USHAI execution system.
- The seven-day OpenAI key expiry does not stop a Render service or guarantee a spending cutoff. A one-week pilot needs an explicitly verified shutdown mechanism, and approval after independent review.

## Offline test command

From the repository root: python -m unittest -v SYNTH_SHAI_staging_gateway.test_openai_chat_gateway

Root `python -m unittest discover -v` now discovers this test package.

The gateway, session, quota and sunset tests use fake providers and fake Render responses; none calls OpenAI or Render. Run `python -m unittest discover -v` from the repository root. No paid credit is required. This folder contains no environment values or API credentials and must not be deployed yet.

## Project status

The gateway is offline research code only. Incorporating these files into the repository is not approval to operate a public service, configure a Render service, connect Android login, invoke the Render sunset helper, or consume OpenAI API credits. Keep 144 HOLD for consequential operations; independent security review and explicit human deployment approval are still required.

## Trusted operator setup — NOT a deployment recipe

Before a pilot, a security reviewer must choose a real identity provider supporting the pinned EdDSA token profile and configure Android authorization-code + PKCE sign-in. The private signing key stays solely with that identity provider. A trusted operator must create a persistent, access-restricted quota database by calling `pilot_security.initialize_store(absolute_path)` outside HTTP, then configure the public verifier key and issuer/audience in a protected server environment. The gateway **cannot authenticate real Android users without that issuer**.

The Render sunset helper has no scheduler and does not verify suspension. A future one-week pilot requires a separate scheduling/monitoring system with private credentials and demonstrated suspension/retries. The helper is dry-run by default; do not supply its execute flags until a human security review and explicit deployment approval.

Project-maintained tests are not a substitute for independent security review. **144 HOLD remains active.**
