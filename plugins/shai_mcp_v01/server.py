"""SYNTH_SHAI MCP adapter for ChatGPT, read-only and offline by default.

Uses the official MCP Python SDK v2. Never expose this development endpoint
to the internet or add remote tools until reviewed authentication is in place.
"""
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from core import shai_status_snapshot, shai_triage_evidence

mcp = MCPServer("SYNTH_SHAI Read-Only Research")
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
)


@mcp.tool(
    name="shai_status",
    title="SHAI research status snapshot",
    description="Return a dated, project-maintained offline evidence snapshot and 144 HOLD limitations. Not live GitHub verification.",
    annotations=READ_ONLY,
)
def shai_status() -> dict:
    """Read-only project status snapshot; no account or network access."""
    return shai_status_snapshot()


@mcp.tool(
    name="shai_evidence_triage",
    title="SHAI evidence intake triage",
    description="Check the shape of a claim's GitHub revision/run reference. No external verification, no approval or execution.",
    annotations=READ_ONLY,
)
def shai_evidence_triage(
    claim: str, source_revision: str = "", evidence_url: str = ""
) -> dict:
    """Return 144 HOLD or REVIEW_REQUIRED; neither authorizes an action."""
    return shai_triage_evidence(claim, source_revision, evidence_url)


if __name__ == "__main__":
    # Local, unauthenticated DEVELOPMENT endpoint only. Not ChatGPT-connected.
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8766)
