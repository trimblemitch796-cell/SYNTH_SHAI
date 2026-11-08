# SYNTH_SHAI OAuth-gated read-only MCP resource server — V0.1

**Status:** unmerged offline research candidate; NOT hosted or ChatGPT-connected; no OAuth provider established; **144 HOLD** for consequential actions.

This separate candidate implements the **resource-server** side of MCP OAuth. It does not build an authorization server, consent page, OAuth client, ChatGPT app, hosted AI model, or secure tunnel. The existing local unauthenticated development server stays localhost-only and unchanged.

## Design

- authenticated_server.py builds an MCPServer with the official SDK's TokenVerifier + AuthSettings, required scope shai:read and exact resource validation
- auth_resource.py refuses startup unless all five trusted configuration values are provided: SHAI_OAUTH_ISSUER, SHAI_MCP_RESOURCE_URL, SHAI_OAUTH_INTROSPECTION_URL, SHAI_OAUTH_CLIENT_ID and SHAI_OAUTH_CLIENT_SECRET
- issuer, resource URL and introspection endpoint MUST all be HTTPS; introspection must be on the same origin as the configured issuer, and resource must end with /mcp
- IntrospectionVerifier sends the bearer token ONLY to the trusted issuer's configured RFC 7662 introspection endpoint with the separate machine-to-machine client credential; it refuses redirects, errors, invalid JSON, malformed active responses, wrong issuer, wrong audience, missing shai:read scope, expired or unbounded tokens, or absent subject/client identity
- no credential or bearer token is committed, reflected in tool output, or deliberately logged
- MCP SDK advertises protected-resource metadata and rejects unauthorized HTTP requests with 401
- the ONLY registered tools are shai_status and shai_evidence_triage, reusing the original deterministic read-only functions
- tests use httpx.MockTransport / in-process ASGI; no real identity provider, public listener, account, tunnel or external network

## How to run the offline tests

Run inside a disposable environment with the isolated MCP SDK requirement:

    python -m pip install -r plugins/shai_mcp_v01/requirements.txt
    python -m unittest discover -s plugins/shai_mcp_v01 -p "test_*.py" -v

The existing repository and old MCP development entry point are not altered.

## Before any real connection

1. Independent technical reviewer examines and adversarially tests verifier, OAuth discovery, issuer trust, TLS termination, host checks, token lifecycle, rate limiting, audit/privacy and supply chain. Project-maintained CI is not sufficient.
2. Owner selects a real OAuth 2.1 authorization server (not created here), registers a protected resource, provisions confidential introspection credentials in a managed secrets store (not GitHub source), ensures proper user-consent/scopes, and confirms refresh-token support. No synthetic OAuth credentials in production.
3. Deploy only behind a hardened HTTPS boundary or vetted Secure MCP Tunnel; restrict filesystem, identity, network and process capabilities, set a real allowed-host list, enforce narrow egress to the identity provider, and verify end-to-end authentication using real test accounts. There is deliberately no public startup script or deployment config in this PR.
4. Confirm your ChatGPT account/workspace actually permits adding a custom read-only MCP plugin on web. This is subject to plan and workspace roles; app setup is not performed by this code.
5. Test read-only calls, repeat/expiry/deny and revocation behaviours. Never add write or autonomous tools until the separately assessed action service passes issue #73 and owner authorization.

This candidate is NOT an authorization for live GitHub actions. Symbolic 444000 cannot substitute for OAuth or the independently reviewed action gate. **144 HOLD remains.**

References:
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/authorization.md
- https://github.com/trimblemitch796-cell/SYNTH_SHAI/issues/21
- https://github.com/trimblemitch796-cell/SYNTH_SHAI/issues/73
