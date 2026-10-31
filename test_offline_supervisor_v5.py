"""Security V5 bounded, fail-closed parent tests. No live side effects."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from offline_approval_v1 import HOLD, SIGNED_FIELDS, canonical
from offline_dispatch_v3 import SIMULATED
from offline_preflight_v3 import PreflightPolicy
from offline_supervisor_v5 import DENIED, _reply, run_bounded_simulation


class DeadlineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = str(Path(tmp.name) / "approval.sqlite")
        self.key = Ed25519PrivateKey.generate()
        public = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        self.keys = {"human": public}
        self.request = {"request_id": "v5-request", "action": "synthetic_review",
                        "plan_sha256": hashlib.sha256(b"test").hexdigest()}
        self.policy = PreflightPolicy(frozenset({"synthetic_review"}))
        self.now = 100000
        self.approval = self.sign()

    def sign(self, **updates):
        payload = {**self.request, "operator_id": "human",
                   "nonce": "v5-nonce-unique-12345", "expires_at": self.now + 30}
        payload.update(updates)
        payload["signature"] = self.key.sign(canonical(
            {k: payload[k] for k in SIGNED_FIELDS})).hex()
        return payload

    def call(self, approval=None, request=None, timeout=5.0):
        message = json.dumps({
            "request": self.request if request is None else request,
            "approval": self.approval if approval is None else approval
        }).encode("utf-8")
        return run_bounded_simulation(message, policy=self.policy,
                                      trusted_operator_keys=self.keys,
                                      trusted_database_path=self.db, now=self.now,
                                      deadline_seconds=timeout)

    def test_valid_synthetic_worker_completes(self):
        self.assertEqual(self.call()["decision"], SIMULATED)

    def test_replay_denied_across_workers(self):
        self.assertEqual(self.call()["decision"], SIMULATED)
        self.assertEqual(self.call()["decision"], HOLD)

    def test_forgery_denied(self):
        self.assertEqual(self.call(approval=dict(self.approval, signature="00"*64)), DENIED)

    def test_prohibited_action_denied(self):
        new = dict(self.request, action="transfer_funds")
        self.assertEqual(self.call(request=new, approval=self.sign(action="transfer_funds")), DENIED)

    def test_malformed_json_denied(self):
        self.assertEqual(run_bounded_simulation(
            b'not json', policy=self.policy, trusted_operator_keys=self.keys,
            trusted_database_path=self.db, now=self.now), DENIED)

    def test_oversize_input_denied_before_spawn(self):
        with patch("offline_supervisor_v5.multiprocessing.get_context") as fake:
            result = run_bounded_simulation(
                b'x' * 16385, policy=self.policy, trusted_operator_keys=self.keys,
                trusted_database_path=self.db, now=self.now)
        self.assertEqual(result, DENIED)
        fake.assert_not_called()

    def test_invalid_deadline_denied_before_spawn(self):
        for limit in (0, -1, float("nan"), float("inf"), True, 11):
            with self.subTest(limit=limit), patch("offline_supervisor_v5.multiprocessing.get_context") as fake:
                self.assertEqual(self.call(timeout=limit), DENIED)
                fake.assert_not_called()

    def test_timeout_terminates_unresponsive_child(self):
        # Test-only fake process: ensures parent owns timeout response and
        # invokes termination; no untrusted callback enters production API.
        class HangingProcess:
            pid = 12345
            exitcode = None
            terminated = False
            def start(self): pass
            def is_alive(self): return not self.terminated
            def terminate(self): self.terminated = True
            def kill(self): self.terminated = True
            def join(self, timeout=None): pass

        class SilentPipe:
            def send_bytes(self, raw): pass
            def poll(self, timeout): return False
            def close(self): pass

        class FakeContext:
            def __init__(self):
                self.worker = HangingProcess()
                self.pipe = SilentPipe()
            def Pipe(self, duplex=True): return self.pipe, SilentPipe()
            def Process(self, **kwargs): return self.worker

        ctx = FakeContext()
        with patch("offline_supervisor_v5.multiprocessing.get_context", return_value=ctx):
            self.assertEqual(self.call(timeout=0.01), DENIED)
        self.assertTrue(ctx.worker.terminated)

    def test_invalid_worker_reply_denied(self):
        for raw in (b'{}', b'[]', b'not json', b'{"decision":"ALLOW"}',
                    b'{"decision":"SIMULATED_REVIEW_ONLY","simulated_effect":"hacked"}'):
            with self.subTest(raw=raw):
                self.assertEqual(_reply(raw), DENIED)

    def test_success_reply_exact_schema_only(self):
        ok = b'{"decision":"SIMULATED_REVIEW_ONLY","simulated_effect":"synthetic_review_recorded"}'
        self.assertEqual(_reply(ok)["decision"], SIMULATED)
        self.assertEqual(_reply(ok[:-1] + b',"execute":true}'), DENIED)


if __name__ == "__main__":
    unittest.main()
