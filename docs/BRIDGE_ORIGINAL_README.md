# SYNTH_SHAI WhatsApp Bridge V1 — inbound-only safety demonstration

**Not live. Not deployed. No AI provider APIs connected. No outbound messages.** This is a minimal standard-library Python proof of concept for Meta WhatsApp Cloud API webhook verification. It is deliberately *not* a WhatsApp chatbot yet.

## What is implemented
- `GET /webhook` returns Meta's `hub.challenge` only for the correct verify token.
- `POST /webhook` checks `X-Hub-Signature-256` against the raw request body using the Meta App Secret; absent or incorrect signatures fail closed.
- Minimal text-message interpretation returns `144 HOLD`, and *drafts* a human-review response for `SHAI`, `/compare`, `/status`, or other text.
- Replies are **never sent**. No real model or Meta outbound API calls are made. No phone numbers or message contents are stored in logs.

## Test offline
```sh
python3 -m unittest discover -v
```

## Run locally (inbound test only)
```sh
export SHAI_VERIFY_TOKEN='choose-a-long-random-secret'
export SHAI_META_APP_SECRET='paste-from-Meta-App-Settings-securely'
python3 bridge.py
```
The server binds to `127.0.0.1:8080` by default. For deployment behind an HTTPS reverse proxy, set `SHAI_HOST=0.0.0.0`, use strict ingress limits, durable event-id deduplication, secure credential management and rate limiting. Do not expose the starter directly to the public internet.

## Meta prerequisites (owner action needed)
1. Visit https://developers.facebook.com/apps/ and create/select an app with the WhatsApp use case.
2. Configure the WhatsApp Cloud API test phone number.
3. Obtain a *Phone Number ID*, test access token, and **App Secret**. Do not paste credentials into chats or GitHub.
4. Deploy an approved, reviewed HTTPS webhook endpoint; set its callback URL to `https://YOUR_HOST/webhook`, choose the same verify token as the server, and subscribe to `messages`.
5. Independently test verification, signatures, retries, duplicate events and message handling before enabling outbound API calls.

## Next build gates
- Add durable replay/idempotency store (Meta retries webhooks).
- Queue human-review tasks; require explicit authenticated approval before sending a draft.
- Add allowlisted recipients, rate limits, retention controls, error handling and the Meta 24h messaging-policy checks.
- Add provider adapters for ChatGPT, Gemini, Claude and Grok as **separate, opt-in integrations**; cross-model comparison is not yet implemented.
- Run tests in CI, perform threat modeling and independent review before live use.

The original GitHub repository is unchanged. This starter is for review and testing, not evidence of independent security validation.
