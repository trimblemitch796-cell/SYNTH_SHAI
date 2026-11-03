# SYNTH_SHAI Android V0.3 — online conversation research prototype

Status: **144 HOLD / NOT DEPLOYED**.

This branch starts from the Android V0.2 review branch. The first V0.3 change is a **Python loopback-only gateway experiment**, not an Android-integrated or hosted AI service. It has no Android networking implementation yet.

- Model default: `gpt-6-luna` (requires verified model access).
- OpenAI Responses API, `store: false`, `tools: []`, 300 output tokens maximum.
- Secret key read from the server environment; never embed it in Android or commit it to GitHub.
- Only binds to `127.0.0.1:8765`. This is **not reachable from a separate Android phone**.
- No web search, device operations, WhatsApp, autonomous execution, or tool calling.
- No persistent conversation memory yet.
- Mocked unit tests are provided; passing these would **not** establish security or real API availability.

**Important limits:** This development server has no authentication, TLS, rate limiting, robust privacy policy, independent authorization enforcement, or production request concurrency controls. Do not bind to `0.0.0.0`, forward ports, or deploy it. A model instruction mentioning `144 HOLD` is not a security boundary. Before any phone-to-server integration, design and independently review a proper authenticated gateway, strict budget and quotas, transport security, server-side action isolation, and consent/privacy controls.

Offline unit test command from repository root:

```bash
python -m unittest discover -s prototypes/android_v03 -p 'test_*.py'
```

No API calls or charges are made by those tests. A real OpenAI test requires separate authorization, completed API setup and cost controls.
