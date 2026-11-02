"""Offline negative control: V4 rlimits are NOT an OS filesystem/network sandbox.

This demonstrates missing restrictions using disposable files and an
unconnected socket. Passing is NOT proof of isolation. The child target is
test-only and must never be exposed as a worker capability.
"""
import json
import multiprocessing
import socket
import sys
import tempfile
import unittest
from pathlib import Path

from offline_sandbox_v4 import apply_limits

_MARKER = "synthetic-no-secrets-v5-negative-control"


def _test_only_probe(send_connection, fake_host_path, fake_write_path):
    """Check ambient access after V4 rlimits; no real data or network traffic."""
    observations = {
        "limits_applied": apply_limits(),
        "fake_host_readable": False,
        "fake_host_writable": False,
        "inet_socket_creatable": False,
    }
    if observations["limits_applied"]:
        try:
            observations["fake_host_readable"] = (
                Path(fake_host_path).read_text(encoding="utf-8") == _MARKER
            )
        except OSError:
            pass
        try:
            Path(fake_write_path).write_text(_MARKER, encoding="utf-8")
            observations["fake_host_writable"] = (
                Path(fake_write_path).read_text(encoding="utf-8") == _MARKER
            )
        except OSError:
            pass
        # Construct only; do not bind, connect, send, or contact any service.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM):
                observations["inet_socket_creatable"] = True
        except OSError:
            pass
    try:
        send_connection.send_bytes(json.dumps(observations).encode("utf-8"))
    finally:
        send_connection.close()


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux-only V4 control")
class V5MissingIsolationNegativeControl(unittest.TestCase):
    def test_resource_limits_do_not_isolate_host_files_or_inet_sockets(self):
        """Gap baseline: fake host files and socket creation remain accessible.

        Passing proves the isolation restrictions are absent in the tested
        environment, not that the worker is a secure sandbox. Once the future
        trusted OS sandbox exists, replace this with denial acceptance tests.
        """
        with tempfile.TemporaryDirectory(prefix="shai-v5-fake-host-") as root:
            fake_host_path = Path(root, "publicly-invented-fixture.txt")
            fake_write_path = Path(root, "fake-worker-output.txt")
            fake_host_path.write_text(_MARKER, encoding="utf-8")
            ctx = multiprocessing.get_context("spawn")
            recv_connection, send_connection = ctx.Pipe(duplex=False)
            worker = ctx.Process(
                target=_test_only_probe,
                args=(send_connection, str(fake_host_path), str(fake_write_path)),
            )
            try:
                worker.start()
                send_connection.close()
                self.assertTrue(recv_connection.poll(12), "probe had no response")
                result = json.loads(recv_connection.recv_bytes(1024))
                worker.join(4)
                self.assertEqual(worker.exitcode, 0)
                self.assertTrue(result["limits_applied"], result)
                self.assertTrue(result["fake_host_readable"], result)
                self.assertTrue(result["fake_host_writable"], result)
                self.assertTrue(result["inet_socket_creatable"], result)
                self.assertEqual(fake_write_path.read_text(encoding="utf-8"), _MARKER)
            finally:
                recv_connection.close()
                send_connection.close()
                if worker.is_alive():
                    worker.terminate()
                    worker.join(2)
                if worker.is_alive():
                    worker.kill()
                    worker.join(2)


if __name__ == "__main__":
    unittest.main()
