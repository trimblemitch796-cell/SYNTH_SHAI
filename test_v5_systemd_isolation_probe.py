"""Bounded offline contract tests: no systemd manager needed for mock paths."""
import json
import subprocess
import unittest
from unittest.mock import patch

import v5_systemd_isolation_probe as v5


class SystemdIsolationExperimentTests(unittest.TestCase):
    def setUp(self):
        self.fixed_nonce = "a" * 32

    def call_with_result(self, output, code=0):
        with (patch.object(v5.sys, "platform", "linux"),
              patch.object(v5.shutil, "which", return_value="/usr/bin/systemd-run"),
              patch.object(v5.secrets, "token_hex",
                           side_effect=[self.fixed_nonce, "b" * 16]),
              patch.object(v5.subprocess, "run",
                           return_value=subprocess.CompletedProcess(
                               [], code, output, "")) as run):
            result = v5.run_offline_probe()
            return result, run

    def ok_message(self):
        return json.dumps({
            "kind": "synthetic_kernel_probe",
            "nonce": self.fixed_nonce,
            "file_read_denied": True,
            "file_write_denied": True,
            "inet_socket_denied": True,
        })

    def test_missing_manager_denies_without_subprocess(self):
        with (patch.object(v5.sys, "platform", "linux"),
              patch.object(v5.shutil, "which", return_value=None),
              patch.object(v5.subprocess, "run") as run):
            self.assertEqual(v5.run_offline_probe().decision, v5.HOLD)
            run.assert_not_called()

    def test_nonlinux_denied_before_launch(self):
        with patch.object(v5.sys, "platform", "darwin"):
            self.assertEqual(v5.run_offline_probe().decision, v5.HOLD)

    def test_fixed_manager_owned_properties_and_target(self):
        result, run = self.call_with_result(self.ok_message())
        self.assertEqual(result.decision, v5.OBSERVED)
        args, kwargs = run.call_args
        argv = args[0]
        self.assertEqual(argv[0], "/usr/bin/systemd-run")
        for mandatory in (
            "--user", "--quiet", "--wait", "--pipe", "--collect",
            "--service-type=exec",
            "--property=ProtectSystem=strict",
            "--property=PrivateNetwork=yes",
            "--property=RestrictAddressFamilies=AF_UNIX",
            "--property=KillMode=control-group",
            "--property=SystemCallFilter=~@mount",
            "--property=NoNewPrivileges=yes",
        ):
            self.assertIn(mandatory, argv)
        self.assertEqual(argv[argv.index("--") + 1], v5.sys.executable)
        self.assertEqual(argv[argv.index("--") + 3], "--fixture-child")
        self.assertTrue(any(x.startswith("--property=InaccessiblePaths=")
                            for x in argv))
        self.assertEqual(kwargs["timeout"], 12)
        self.assertFalse(kwargs["check"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)

    def test_service_failure_does_not_trust_success_looking_reply(self):
        result, _ = self.call_with_result(self.ok_message(), code=1)
        self.assertEqual(result.decision, v5.HOLD)

    def test_wrong_nonce_denied(self):
        message = json.loads(self.ok_message())
        message["nonce"] = "wrong"
        result, _ = self.call_with_result(json.dumps(message))
        self.assertEqual(result.decision, v5.HOLD)

    def test_malformed_duplicate_extra_and_false_denials_rejected(self):
        cases = [
            "", "not-json", "[]", "{}",
            self.ok_message() + "other text",
            self.ok_message()[:-1] + ',"nonce":"abc"}',
            self.ok_message()[:-1] + ',"execute":true}',
            self.ok_message().replace(
                '"file_read_denied": true', '"file_read_denied": false'),
            self.ok_message().replace(
                '"inet_socket_denied": true', '"inet_socket_denied": 1'),
            "x" * 2048,
        ]
        for case in cases:
            with self.subTest(case=case[:35]):
                result, _ = self.call_with_result(case)
                self.assertEqual(result.decision, v5.HOLD)

    def test_manager_timeout_is_hold_cleanup_unverified(self):
        with (patch.object(v5.sys, "platform", "linux"),
              patch.object(v5.shutil, "which",
                           return_value="/usr/bin/systemd-run"),
              patch.object(v5.subprocess, "run",
                           side_effect=subprocess.TimeoutExpired(
                               "systemd-run", 12))):
            result = v5.run_offline_probe()
            self.assertEqual(result.decision, v5.HOLD)
            self.assertIn("cleanup_unverified", result.reason)

    def test_live_host_only_returns_hold_or_restricted_probe(self):
        # Environment-specific smoke check. CI passing does not imply a real
        # isolated unit launched; most CI hosts have no user systemd manager.
        if not v5.sys.platform.startswith("linux"):
            self.skipTest("not Linux")
        result = v5.run_offline_probe()
        self.assertIn(result.decision, (v5.HOLD, v5.OBSERVED))
        if result.decision == v5.OBSERVED:
            self.assertEqual(result.reason,
                             "all_three_synthetic_denials_observed")
        else:
            self.assertNotEqual(result.reason,
                                "all_three_synthetic_denials_observed")


if __name__ == "__main__":
    unittest.main()
