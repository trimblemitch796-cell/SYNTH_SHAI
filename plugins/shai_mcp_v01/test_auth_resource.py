"""Offline verifier tests: all identity-provider responses use httpx.MockTransport."""
import asyncio
import json
import time
import unittest
from unittest.mock import patch

import httpx

from mcp import Client
from auth_resource import IntrospectionVerifier, ResourceSettings, _SCOPE
from authenticated_server import build_authenticated_server, from_environment


def settings():
    return ResourceSettings(
        issuer="https://login.example.test/tenant",
        resource="https://research.example.test/mcp",
        introspection="https://login.example.test/tenant/oauth2/introspect",
        client_id="fixture-introspection-client",
        client_secret="FICTIONAL-DO-NOT-USE",
    )


def valid_document():
    return {
        "active": True,
        "iss": settings().issuer,
        "aud": settings().resource,
        "scope": "shai:read",
        "exp": int(time.time()) + 120,
        "client_id": "demo-application",
        "sub": "demo-user",
    }


class SettingsTests(unittest.TestCase):
    def test_missing_config_refuses_to_start(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                from_environment()

    def test_plaintext_introspection_rejected(self):
        with self.assertRaises(ValueError):
            ResourceSettings(
                settings().issuer, settings().resource,
                "http://login.example.test/introspect", "id", "secret"
            )

    def test_introspection_cross_origin_rejected(self):
        with self.assertRaises(ValueError):
            ResourceSettings(
                settings().issuer, settings().resource,
                "https://untrusted.example.test/introspect", "id", "secret"
            )

    def test_resource_must_be_https_mcp_endpoint(self):
        with self.assertRaises(ValueError):
            ResourceSettings(settings().issuer, "http://127.0.0.1:8766/mcp",
                             settings().introspection, "id", "secret")
        with self.assertRaises(ValueError):
            ResourceSettings(settings().issuer, "https://research.example.test/other",
                             settings().introspection, "id", "secret")

    def test_missing_client_secret_rejected(self):
        with self.assertRaises(ValueError):
            ResourceSettings(settings().issuer, settings().resource,
                             settings().introspection, "id", "")

    def test_no_unapproved_tools_exposed(self):
        async def inspect():
            async with Client(build_authenticated_server(settings())) as client:
                result = await client.list_tools()
                return {tool.name for tool in result.tools}
        self.assertEqual(asyncio.run(inspect()), {"shai_status", "shai_evidence_triage"})


class IntrospectionTests(unittest.IsolatedAsyncioTestCase):
    async def checked(self, data, *, status=200, raw=False):
        seen = []
        def handle(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(status, text=data if raw else json.dumps(data))
        verifier = IntrospectionVerifier(settings(), transport=httpx.MockTransport(handle))
        token = await verifier.verify_token("fictional-fixture-token")
        self.assertEqual(len(seen), 1)
        self.assertEqual(str(seen[0].url), settings().introspection)
        self.assertEqual(seen[0].method, "POST")
        self.assertIn("Basic ", seen[0].headers.get("Authorization", ""))
        return token

    async def test_valid_token_scoped_to_exact_resource_accepted(self):
        token = await self.checked(valid_document())
        self.assertIsNotNone(token)
        self.assertEqual(token.resource, settings().resource)
        self.assertEqual(token.subject, "demo-user")
        self.assertIn(_SCOPE, token.scopes)

    async def test_inactive_token_rejected(self):
        self.assertIsNone(await self.checked({**valid_document(), "active": False}))

    async def test_wrong_audience_rejected(self):
        self.assertIsNone(await self.checked({**valid_document(), "aud": "https://different.test/mcp"}))

    async def test_wrong_scope_rejected(self):
        self.assertIsNone(await self.checked({**valid_document(), "scope": "files:write"}))

    async def test_expired_rejected(self):
        self.assertIsNone(await self.checked({**valid_document(), "exp": int(time.time()) - 2}))

    async def test_boolean_expiry_rejected(self):
        self.assertIsNone(await self.checked({**valid_document(), "exp": True}))

    async def test_missing_principal_rejected(self):
        self.assertIsNone(await self.checked({**valid_document(), "sub": ""}))
        self.assertIsNone(await self.checked({**valid_document(), "client_id": None}))

    async def test_wrong_issuer_rejected(self):
        self.assertIsNone(await self.checked({**valid_document(), "iss": "https://evil.test"}))

    async def test_nonboolean_active_rejected(self):
        self.assertIsNone(await self.checked({**valid_document(), "active": "true"}))

    async def test_bad_status_rejected(self):
        self.assertIsNone(await self.checked(valid_document(), status=503))

    async def test_bad_json_rejected(self):
        self.assertIsNone(await self.checked("not JSON", raw=True))

    async def test_oversized_response_rejected(self):
        self.assertIsNone(await self.checked("x" * 20000, raw=True))

    async def test_no_redirect_followed(self):
        self.assertIsNone(await self.checked({}, status=302))

    async def test_fake_token_rejected_before_network(self):
        calls = []
        def handle(request):
            calls.append(request)
            raise AssertionError("Network attempted for invalid token")
        verifier = IntrospectionVerifier(settings(), transport=httpx.MockTransport(handle))
        for value in ("", "with spaces", "a" * 4097, "bad\nline"):
            self.assertIsNone(await verifier.verify_token(value))
        self.assertEqual(calls, [])

    async def test_transport_failure_fails_closed(self):
        def fail(request):
            raise httpx.ConnectError("synthetic offline outage")
        verifier = IntrospectionVerifier(settings(), transport=httpx.MockTransport(fail))
        self.assertIsNone(await verifier.verify_token("synthetic-token"))


if __name__ == "__main__":
    unittest.main()
