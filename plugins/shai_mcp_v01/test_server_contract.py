"""MCP SDK contract smoke tests. Requires the separate plugin requirements."""
import unittest

import server


class MCPAdapterTests(unittest.TestCase):
    def test_sdk_server_initializes(self):
        self.assertIsNotNone(server.mcp)
        self.assertTrue(server.READ_ONLY.read_only_hint)
        self.assertFalse(server.READ_ONLY.destructive_hint)
        self.assertFalse(server.READ_ONLY.open_world_hint)
        wire = server.READ_ONLY.model_dump(by_alias=True)
        self.assertTrue(wire["readOnlyHint"])
        self.assertFalse(wire["destructiveHint"])
        self.assertFalse(wire["openWorldHint"])

    def test_exposed_handlers_remain_read_only(self):
        self.assertFalse(server.shai_status()["tool_policy"]["external_calls"])
        result = server.shai_evidence_triage(
            "444000 deploy", "13987e18d172f334a202c54f38e28782a4e45fcc",
            "https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/41740315033"
        )
        self.assertFalse(result["approval_granted"])
        self.assertEqual(result["consequential_action_state"], "144 HOLD")


if __name__ == "__main__":
    unittest.main()
