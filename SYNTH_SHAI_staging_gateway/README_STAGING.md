# SYNTH_SHAI — isolated staging chat gateway (review only)

**144 HOLD. No deployment or merge authorised.** This is a narrow proof-of-concept, not a production system, public service, or Android-ready authentication design.

## Boundaries

- POST /chat accepts only a JSON object with the single field "message". No tool calling, shell, file access, autonomous workflows, financial functions, or external action handlers.
- Requires SHAI_GATEWAY_TOKEN (32+ characters) in the server's environment for Authorization Bearer authentication. This shared test token MUST NOT be embedded in a distributed Android APK. Public mobile access requires independently reviewed, revocable per-user/session authentication.
- Reads OPENAI_API_KEY only from the server environment; it is never accepted from incoming HTTP. Missing configuration fails closed.
- Body limit 4,096 bytes, message limit 2,000 characters, single-process rate limit 5 valid requests per minute, upstream request timeout 12 seconds, maximum model output 256 tokens.
- Fixed provider endpoint: https://api.openai.com/v1/responses; no tools parameter. Provider errors are generic; request data and auth headers are not deliberately logged. The provider call uses store: false.
- Binds to 127.0.0.1 ONLY; it cannot serve Render's public ingress as written. No deployment configuration is provided.
- **Pilot switch defaults OFF.** The trusted server operator must explicitly set `SHAI_PILOT_ENABLED=1` and an absolute, future UTC `SHAI_PILOT_DEADLINE_UTC` such as `2026-11-13T07:00:00Z`; the timestamp must be at most seven days away on every request. Invalid, expired, missing, or disabled settings fail closed (`503 pilot_closed`). The absolute cutoff is not extended by application restarts. **This stops new chat requests, NOT hosting billing or active containers.** No pilot should be enabled until the external shutdown and security review are complete.
- A real deployment needs separately reviewed TLS, mobile authentication, cross-instance abuse/rate controls, credential rotation, incident response, budgeting, safe shutdown, logging, load limits and code isolation. This gateway is NOT wired into the existing SHAI/USHAI execution system.
- The seven-day OpenAI key expiry does not stop a Render service or guarantee a spending cutoff. A one-week pilot needs an explicitly verified shutdown mechanism, and approval after independent review.

## Offline test command

From the repository root: python -m unittest -v SYNTH_SHAI_staging_gateway.test_openai_chat_gateway

Root `python -m unittest discover -v` now discovers this test package.

The 20 tests use a local fake provider and never call the OpenAI API; no paid credit is required. This folder contains no environment values or API credentials and must not be deployed yet.

## Project status

The staging gateway is only a research candidate for review in SYNTH_SHAI. Keep 144 HOLD for consequential operations. Do not merge to main or create a Render service based only on these tests.
