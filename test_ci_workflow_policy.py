"""Offline policy check for .github/workflows (no YAML dependency: plain text rules).
Every action is pinned to a full 40-hex commit SHA, every workflow declares
read-only `contents: read` permissions, and the 3.13 leak-guard job exists."""
import re
import unittest
from pathlib import Path

WORKFLOWS = sorted((Path(__file__).resolve().parent / ".github" / "workflows").glob("*.yml"))


class WorkflowPolicyTests(unittest.TestCase):
    def test_workflows_found(self):
        self.assertTrue(WORKFLOWS)

    def test_actions_pinned_by_full_sha(self):
        for wf in WORKFLOWS:
            for line in wf.read_text().splitlines():
                m = re.match(r"\s*-?\s*uses:\s*(\S+)", line)
                if m:
                    with self.subTest(workflow=wf.name, uses=m.group(1)):
                        self.assertRegex(m.group(1), r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")

    def test_read_only_permissions(self):
        for wf in WORKFLOWS:
            text = wf.read_text()
            with self.subTest(workflow=wf.name):
                self.assertRegex(text, r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$")
                self.assertNotRegex(text, r":\s*write\b")
                self.assertNotIn("pull_request_target", text)

    def test_py313_leak_guard_job(self):
        text = (Path(__file__).resolve().parent / ".github/workflows/verification.yml").read_text()
        self.assertIn("  offline-verification:", text)          # required check name unchanged
        job = text.split("offline-verification-py313:", 1)[1]
        self.assertIn("python-version: '3.13'", job)
        self.assertIn("SHAI_REQUIRE_LEAK_GUARD: '1'", job)
        self.assertIn("-W error::ResourceWarning", job)


if __name__ == "__main__":
    unittest.main()
