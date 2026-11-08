# SYNTH_SHAI ChatGPT MCP — read-only research prototype V0.1

**Status: offline/review only. Not installed in ChatGPT. Not deployed. 144 HOLD.**

This is a small, restricted Model Context Protocol (MCP) server. In a future, explicitly authorized connection, **ChatGPT provides the conversation intelligence** and this SHAI adapter provides deterministic, read-only tools. It does not create a new independent AI model.

The Android V0.2.3 project and the separate V0.3 API gateway are unchanged.

## Exposed tools

- **shai_status** — returns a dated, hard-coded public-repository evidence snapshot and 144 HOLD limitations. Not a live GitHub query.
- **shai_evidence_triage** — checks only the format of a claim, a full commit SHA and a SYNTH_SHAI Actions run URL. It never authenticates those inputs or grants authority. It returns REVIEW_REQUIRED or 144 HOLD, never PASS. The original claim is not reflected in results; a SHA-256 digest is returned instead.

No file modifications, execution adapters, provider API keys, account integrations, or outbound requests are used.

## Offline development checks

Python 3.11+ and a separate virtual environment are recommended. Do not install the MCP dependencies into the main SYNTH_SHAI environment.

~~~sh
python -m venv .venv-shai-mcp
. .venv-shai-mcp/bin/activate
python -m pip install -r plugins/shai_mcp_v01/requirements.txt
python -m unittest discover -s plugins/shai_mcp_v01 -p 'test_*.py' -v
~~~

The pure-core unit tests use only Python's standard library:

~~~sh
python -m unittest discover -s plugins/shai_mcp_v01 -p 'test_core.py' -v
~~~

For a local-only protocol inspection, launch:

~~~sh
python plugins/shai_mcp_v01/server.py
~~~

The SDK listens on **127.0.0.1:8766/mcp** using Streamable HTTP. This development endpoint has **no authentication**. Do not expose it to public networks, forward ports, or use a public tunnel. No hosting or ChatGPT connection is included in this PR.

## What must happen before ChatGPT can call it

ChatGPT requires a remote secured MCP endpoint or an approved secure tunnel. Connection is controlled separately by account/workspace permissions and currently uses ChatGPT **web**, not mobile setup.

A later review must cover authenticated identity/OAuth, HTTPS, scoped permissions, quotas/rate limits, privacy/data minimization, logging without sensitive inputs, independent testing, and a separate explicit user action to connect the plugin in ChatGPT. This prototype is **not** a deployed MCP service.

## Persistent limits

- No GitHub writes, CI dispatch, WhatsApp messaging, financial actions, medical diagnosis, accounts or hardware control.
- No independent OS isolation/security certification, no real-time GitHub verification or true evidence authentication.
- "444000" and "144 HOLD" are symbols in this design; a tool result is not permission.
- Every decision remains **144 HOLD for consequential real-world actions**.
- CI success is project-maintained evidence, not independent audit.
- The Android build is preserved completely.

## Primary references

- https://developers.openai.com/plugins/build/mcp-server
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- https://py.sdk.modelcontextprotocol.io/

**Connection before control. Truth before belief. 144 HOLD.**
