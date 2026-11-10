# SYNTH_SHAI instant chat — review-only clients

**Status: 144 HOLD. Not online, deployed, or approved for public, child, or mobile use.**

This directory holds a dependency-free responsive browser client and a Python
terminal client for the existing SYNTH_SHAI_staging_gateway /chat endpoint.
It does not modify the gateway, Android app, authentication service or existing
execution boundaries. No tools, external actions, analytics, or autonomous
capabilities are enabled.

## Contract

- HTTPS/same-origin POST /chat with exactly a JSON message field and a separately
  issued short-lived SHAI session JWT. Google ID tokens and OpenAI keys are
  not acceptable session tokens.
- A successful gateway response is JSON with one reply field.
- The browser displays plain text only. Transcripts and token inputs are
  volatile, not stored persistently. The terminal client does not persist chats.
- Input lengths, request size, response shape, gateway errors, and HTTPS-only
  operation are checked. No automatic retry or login bypass exists.
- The upstream server remains loopback-only, pilot-disabled by default and
  protected by session verification, revocation and quotas.

## Offline test commands

From repository root, with Python 3 and Node.js installed:

    python3 -m unittest discover -s instant-chat -p 'test_*.py' -v
    node --test instant-chat/client.test.mjs

These tests inject fake HTTP responses, use no provider credentials, do not call
OpenAI, and do not prove real-world latency, server security or production safety.

An HTML-only local view can be opened with:

    python3 -m http.server --bind 127.0.0.1 8765 --directory instant-chat

It displays the UI but **Send cannot work** on that static server because it
does not provide the protected /chat endpoint. A reviewed HTTPS deployment must
serve the UI and gateway at the same origin.

The optional terminal client is invoked as:

    python3 instant-chat/instant_chat_cli.py

Only after the separate security and deployment review can a trusted operator
supply SHAI_GATEWAY_ORIGIN and SHAI_SESSION_JWT through a protected local
environment. Never commit session tokens to GitHub or paste them into an
unreviewed site.

## Hard blockers before online use

1. Trusted HTTPS origin and externally reviewed static asset security.
2. Real identity provider, reviewed token issuer, logout and revocation.
3. Durable cross-instance quota, replay protection, abuse and spending limits.
4. Tested scheduler / hosting shutdown and independent evidence.
5. Explicit human authorization to configure hosting, enable the pilot,
   connect Android, access live provider credits, or admit public/child users.

The existing draft authentication work in PRs #105 and #106 is not a deployed
service. A user-facing sign-in UI must replace the operator token textbox
before any public release. Do not put signing keys, OPENAI_API_KEY or Google
secrets in a browser or Android APK.

**No deployment, merge or change to 144 HOLD is authorised by this PR.**
