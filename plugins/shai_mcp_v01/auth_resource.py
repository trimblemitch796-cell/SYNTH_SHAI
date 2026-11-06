"""Opt-in OAuth resource-server boundary for SHAI's two read-only MCP tools.

UNDEPLOYED candidate. No OAuth issuer, credential, listener or account is created.
Verification is by a separately trusted HTTPS OAuth introspection provider.
Fail closed unless the issuer, audience, scope, expiry and user are all verified.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import os
import time
from urllib.parse import urlsplit

import httpx
from mcp.server.auth.provider import AccessToken


_SCOPE = "shai:read"
_MAX_TOKEN = 4096
_MAX_RESPONSE = 16384


def _https_url(value: str) -> bool:
    if not isinstance(value, str) or not value or value.strip() != value:
        return False
    try:
        u = urlsplit(value)
        return (
            u.scheme == "https" and bool(u.hostname) and bool(u.netloc)
            and u.username is None and u.password is None
            and not u.query and not u.fragment and not any(c.isspace() for c in value)
            and u.port != 0
        )
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True)
class ResourceSettings:
    issuer: str
    resource: str
    introspection: str
    client_id: str
    client_secret: str

    def __post_init__(self):
        if not all(_https_url(x) for x in
                   (self.issuer, self.resource, self.introspection)):
            raise ValueError("Issuer, resource and introspection URLs must use HTTPS")
        a, b = urlsplit(self.issuer), urlsplit(self.introspection)
        if (a.hostname, a.port or 443) != (b.hostname, b.port or 443):
            raise ValueError("Introspection endpoint must share issuer origin")
        if not self.resource.endswith("/mcp"):
            raise ValueError("Resource URL must identify the /mcp endpoint")
        if not isinstance(self.client_id, str) or not self.client_id.strip():
            raise ValueError("Trusted OAuth introspection client id required")
        if not isinstance(self.client_secret, str) or not self.client_secret.strip():
            raise ValueError("Trusted OAuth introspection client secret required")

    @classmethod
    def from_environment(cls):
        names = (
            "SHAI_OAUTH_ISSUER",
            "SHAI_MCP_RESOURCE_URL",
            "SHAI_OAUTH_INTROSPECTION_URL",
            "SHAI_OAUTH_CLIENT_ID",
            "SHAI_OAUTH_CLIENT_SECRET",
        )
        values = [os.environ.get(n, "") for n in names]
        return cls(*values)


class IntrospectionVerifier:
    """Resource-server verification via trusted issuer's RFC 7662 endpoint.

    The only outbound call is an HTTPS request to the configured issuer's
    introspection endpoint. In CI a MockTransport intercepts it; no real
    external network is accessed. Never log tokens or response contents.
    """

    def __init__(self, settings: ResourceSettings, *,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def verify_token(self, token: str) -> AccessToken | None:
        if (not isinstance(token, str) or not token or len(token) > _MAX_TOKEN
                or any(ord(c) < 33 or ord(c) > 126 for c in token)):
            return None
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(3.0),
                follow_redirects=False,
                trust_env=False,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    self.settings.introspection,
                    data={"token": token},
                    auth=(self.settings.client_id, self.settings.client_secret),
                    headers={"Accept": "application/json"},
                )
            if response.status_code != 200 or len(response.content) > _MAX_RESPONSE:
                return None
            doc = response.json()
            if not isinstance(doc, dict) or doc.get("active") is not True:
                return None
            issuer = doc.get("iss")
            if issuer is not None and issuer != self.settings.issuer:
                return None
            aud = doc.get("aud")
            if isinstance(aud, str):
                audience_matches = aud == self.settings.resource
            elif isinstance(aud, list):
                audience_matches = (
                    bool(aud) and all(isinstance(s, str) for s in aud)
                    and self.settings.resource in aud
                )
            else:
                audience_matches = False
            if not audience_matches:
                return None
            raw_scopes = doc.get("scope")
            if not isinstance(raw_scopes, str):
                return None
            scopes = raw_scopes.split()
            if _SCOPE not in scopes:
                return None
            expiry = doc.get("exp")
            if type(expiry) not in (int, float) or not math.isfinite(expiry):
                return None
            if expiry <= time.time() or expiry > time.time() + 86400:
                return None
            sub = doc.get("sub")
            client_id = doc.get("client_id")
            if not isinstance(sub, str) or not sub.strip():
                return None
            if not isinstance(client_id, str) or not client_id.strip():
                return None
            return AccessToken(
                token=token, client_id=client_id, subject=sub,
                scopes=scopes, resource=self.settings.resource,
                expires_at=int(expiry), claims={"iss": self.settings.issuer},
            )
        except (httpx.HTTPError, ValueError, TypeError, KeyError, OverflowError):
            return None
