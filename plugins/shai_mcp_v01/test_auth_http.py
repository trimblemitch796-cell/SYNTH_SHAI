"""Local ASGI HTTP bearer-boundary regression tests, without any listener."""
import json
import time
import unittest

import httpx

from auth_resource import IntrospectionVerifier
from authenticated_server import build_authenticated_server
from test_auth_resource import settings, valid_document

BODY = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
HEADERS = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
    "mcp-protocol-version": "2025-06-18",
}


class OAuthHTTPBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_and_wrong_bearer_unauthorized(self):
        seen = []
        def introspect(request):
            seen.append(request)
            return httpx.Response(200, json={"active": False})
        verifier = IntrospectionVerifier(settings(), transport=httpx.MockTransport(introspect))
        mcp = build_authenticated_server(settings(), verifier=verifier)
        app = mcp.streamable_http_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost",
        ) as client:
            missing = await client.post("/mcp", headers=HEADERS, json=BODY)
            self.assertEqual(missing.status_code, 401)
            self.assertIn("Bearer", missing.headers.get("www-authenticate", ""))
            self.assertEqual(seen, [], "Missing bearer must not reach token verifier")

            invalid = await client.post(
                "/mcp", headers={**HEADERS, "authorization": "Bearer wrong-fixture-token"},
                json=BODY,
            )
            self.assertEqual(invalid.status_code, 401)
            self.assertEqual(len(seen), 1)

    async def test_oauth_metadata_discoverable_without_token(self):
        verifier = IntrospectionVerifier(
            settings(),
            transport=httpx.MockTransport(
                lambda req: httpx.Response(503, json={})
            ),
        )
        mcp = build_authenticated_server(settings(), verifier=verifier)
        app = mcp.streamable_http_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost",
        ) as client:
            response = await client.get("/.well-known/oauth-protected-resource/mcp")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["resource"], settings().resource)
            self.assertIn("shai:read", payload["scopes_supported"])

    async def test_valid_bearer_passes_authentication_layer(self):
        seen = []
        def introspect(request):
            seen.append(request)
            return httpx.Response(200, json=valid_document())
        mcp = build_authenticated_server(
            settings(),
            verifier=IntrospectionVerifier(settings(), transport=httpx.MockTransport(introspect)),
        )
        app = mcp.streamable_http_app()
        async with mcp.session_manager.run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://localhost",
                timeout=5,
            ) as client:
                response = await client.post(
                    "/mcp", headers={**HEADERS, "authorization": "Bearer valid-fixture-token"},
                    json=BODY,
                )
        self.assertNotIn(response.status_code, (401, 403, 500))
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
