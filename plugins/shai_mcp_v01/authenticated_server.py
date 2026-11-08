"""UNDEPLOYED, opt-in OAuth resource-server factory for read-only SHAI MCP.

The existing local development server is unchanged and remains localhost-only.
Importing this module never opens a socket, reads account data, or deploys.
There is intentionally no public listener or automatic startup entry point.
"""
from pydantic import AnyHttpUrl

from mcp.server import MCPServer
from mcp.server.auth.settings import AuthSettings

from auth_resource import IntrospectionVerifier, ResourceSettings
from core import shai_status_snapshot, shai_triage_evidence
from server import READ_ONLY


def build_authenticated_server(settings: ResourceSettings, verifier=None) -> MCPServer:
    """Create a bearer-gated MCP resource server.

    A verifier override is for isolated CI fixtures only, never a deployment
    configuration. Production construction must call from_environment().
    """
    if not isinstance(settings, ResourceSettings):
        raise ValueError("Explicit, validated ResourceSettings required")
    if verifier is None:
        verifier = IntrospectionVerifier(settings)
    mcp = MCPServer(
        "SYNTH_SHAI Read-Only Research (OAuth candidate)",
        token_verifier=verifier,
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(settings.issuer),
            resource_server_url=AnyHttpUrl(settings.resource),
            required_scopes=["shai:read"],
            validate_token_resource=True,
        ),
    )

    @mcp.tool(
        name="shai_status",
        description="Read-only dated SHAI snapshot; not live verification.",
        annotations=READ_ONLY,
    )
    def status() -> dict:
        return shai_status_snapshot()

    @mcp.tool(
        name="shai_evidence_triage",
        description="Syntax-check a research claim reference. Never approve or execute.",
        annotations=READ_ONLY,
    )
    def evidence_triage(claim: str, source_revision: str = "",
                        evidence_url: str = "") -> dict:
        return shai_triage_evidence(claim, source_revision, evidence_url)

    return mcp


def from_environment() -> MCPServer:
    """Fail closed without a separately configured trusted OAuth provider."""
    settings = ResourceSettings.from_environment()
    return build_authenticated_server(settings)
