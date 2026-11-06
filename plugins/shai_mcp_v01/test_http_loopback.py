"""Bounded HTTP MCP smoke test on 127.0.0.1; never a remote plugin deployment.

The server is a disposable local subprocess killed after this one test.
No OpenAI account, key, tunnel, webhook, public network or remote API is used.
"""
import asyncio
import socket
import subprocess
import sys
import unittest
from pathlib import Path

from mcp import Client

PORT = 8766
ADDRESS = "127.0.0.1"
URL = f"http://{ADDRESS}:{PORT}/mcp"


class HTTPTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_loopback_tool_discovery_and_hold(self):
        server_script = Path(__file__).with_name("server.py")
        child = subprocess.Popen(
            [sys.executable, str(server_script)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            listening = False
            for _ in range(60):
                self.assertIsNone(child.poll(), "MCP server exited before loopback startup")
                try:
                    with socket.create_connection((ADDRESS, PORT), timeout=0.2):
                        listening = True
                        break
                except OSError:
                    await asyncio.sleep(0.2)
            self.assertTrue(listening, "Local MCP server did not bind 127.0.0.1")
            async with Client(URL) as client:
                tools = await client.list_tools()
                self.assertEqual(
                    {tool.name for tool in tools.tools},
                    {"shai_status", "shai_evidence_triage"},
                )
                for tool in tools.tools:
                    self.assertTrue(tool.annotations.read_only_hint)
                reply = await client.call_tool("shai_status", {})
                self.assertFalse(reply.is_error)
                combined = "\n".join(
                    item.text for item in reply.content if item.type == "text"
                )
                self.assertIn("144 HOLD", combined)
                self.assertIn("No independently validated operational safety", combined)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=6)


if __name__ == "__main__":
    unittest.main()
