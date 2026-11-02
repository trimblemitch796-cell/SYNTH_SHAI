"""Project-maintained Linux-only V4.1 offline parent lifecycle regression tests."""
import hashlib
import json
import multiprocessing
import os
import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from offline_approval_v1 import HOLD, SIGNED_FIELDS, canonical
from offline_dispatch_v3 import SIMULATED
from offline_parent_v41 import _exchange_with_child, review_offline_once
from offline_preflight_v3 import PreflightPolicy
from offline_worker_v3 import MAX_MESSAGE

_SIM_REPLY = b'{"decision":"SIMULATED_REVIEW_ONLY","simulated_effect":"synthetic_review_recorded"}'


def _hang_after_receive(conn, *, ready):
    conn.recv_bytes(1024)
    ready.set()
    time.sleep(60)


def _hang_before_receive(conn, *, ready):
    ready.set()
    time.sleep(60)


def _crash_after_receive(conn, *, ready):
    conn.recv_bytes(1024)
    ready.set()
    os._exit(49)


def _reply_then_crash(conn, *, ready):
    conn.recv_bytes(1024)
    ready.set()
    conn.send_bytes(_SIM_REPLY)
    os._exit(43)


def _reply_then_hang(conn, *, ready):
    conn.recv_bytes(1024)
    ready.set()
    conn.send_bytes(_SIM_REPLY)
    time.sleep(60)


def _partial_frame_then_hang(conn, *, ready):
    conn.recv_bytes(1024)
    os.write(conn.fileno(), b'\x00\x00\x00\x20' + b'{"decision":')
    ready.set()
    time.sleep(60)


def _ignore_term_and_hang(conn, *, ready):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    conn.recv_bytes(1024)
    ready.set()
    conn.send_bytes(b'{"decision":"144 HOLD","simulated_effect":null}')
    time.sleep(60)


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux resource-limit regression")
class ParentLifecycleTests(unittest.TestCase):
    def assert_hold_and_reaped(self, outcome):
        self.assertEqual(outcome.reply, {"decision": HOLD, "simulated_effect": None}, outcome)
        self.assertTrue(outcome.reaped, outcome)
        self.assertIsNotNone(outcome.exitcode, outcome)
        self.assertTrue(outcome.transport_thread_ended, outcome)

    def run_fault(self, target, *, payload=b'{}', deadline_seconds=3.0,
                  cleanup_grace=0.4, should_start=True):
        ready = multiprocessing.get_context("spawn").Event()
        result = _exchange_with_child(target=target, payload=payload,
                                      kwargs={"ready": ready},
                                      deadline_seconds=deadline_seconds,
                                      cleanup_grace=cleanup_grace)
        if should_start:
            self.assertTrue(ready.is_set(), "child fault fixture never started")
        return result

    def test_child_hangs_after_receive(self):
        result = self.run_fault(_hang_after_receive)
        self.assert_hold_and_reaped(result)
        self.assertEqual(result.reason, "transport_timeout")

    def test_child_hangs_before_receive(self):
        result = self.run_fault(_hang_before_receive, payload=b"x" * MAX_MESSAGE)
        self.assert_hold_and_reaped(result)
        self.assertEqual(result.reason, "transport_timeout")

    def test_child_crashes_without_reply(self):
        result = self.run_fault(_crash_after_receive)
        self.assert_hold_and_reaped(result)
        self.assertNotEqual(result.exitcode, 0)

    def test_success_looking_reply_then_crash(self):
        result = self.run_fault(_reply_then_crash)
        self.assert_hold_and_reaped(result)
        self.assertEqual(result.reason, "abnormal_exit")

    def test_success_looking_reply_then_hang(self):
        result = self.run_fault(_reply_then_hang)
        self.assert_hold_and_reaped(result)
        self.assertIn(result.reason, {"exit_timeout", "transport_timeout"})

    def test_partial_frame_then_hang(self):
        result = self.run_fault(_partial_frame_then_hang)
        self.assert_hold_and_reaped(result)
        self.assertEqual(result.reason, "transport_timeout")

    def test_termination_escalates_to_kill(self):
        result = self.run_fault(_ignore_term_and_hang, deadline_seconds=3,
                                cleanup_grace=0.4)
        self.assert_hold_and_reaped(result)
        self.assertEqual(result.reason, "exit_timeout")
        self.assertEqual(result.exitcode, -signal.SIGKILL)

    def test_valid_worker_review_and_replay(self):
        with tempfile.TemporaryDirectory() as root:
            key = Ed25519PrivateKey.generate()
            keys = {"test": key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw)}
            now = 100000
            request = {"request_id": "v41-parent-test", "action": "synthetic_review",
                       "plan_sha256": hashlib.sha256(b"offline").hexdigest()}
            signed = dict(request, operator_id="test", nonce="parent-once-nonce-000001",
                          expires_at=now + 30)
            signed["signature"] = key.sign(canonical({k: signed[k] for k in SIGNED_FIELDS})).hex()
            payload = json.dumps({"request": request, "approval": signed}).encode("utf-8")
            kwargs = {"policy": PreflightPolicy(frozenset({"synthetic_review"})),
                      "trusted_operator_keys": keys,
                      "trusted_database_path": str(Path(root) / "approval.sqlite"), "now": now}
            valid = review_offline_once(payload, **kwargs, deadline_seconds=5)
            self.assertEqual(valid.reply, {"decision": SIMULATED,
                                           "simulated_effect": "synthetic_review_recorded"}, valid)
            self.assertTrue(valid.reaped, valid)
            self.assertTrue(valid.transport_thread_ended, valid)
            self.assertEqual(valid.exitcode, 0, valid)
            replay = review_offline_once(payload, **kwargs, deadline_seconds=5)
            self.assert_hold_and_reaped(replay)
            self.assertEqual(replay.exitcode, 0)

    def test_invalid_message_denied_before_process_start(self):
        result = self.run_fault(_crash_after_receive, payload=b'x' * (MAX_MESSAGE + 1),
                                should_start=False)
        self.assertEqual(result.reply, {"decision": HOLD, "simulated_effect": None})
        self.assertEqual(result.reason, "invalid_input")
        self.assertIsNone(result.exitcode)  # No child was launched


if __name__ == "__main__":
    unittest.main()
