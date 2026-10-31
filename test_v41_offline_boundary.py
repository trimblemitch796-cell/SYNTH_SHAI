"""V4.1 offline boundary regression checks; NOT sandbox validation or an audit."""
import hashlib
import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from offline_approval_v1 import HOLD, SIGNED_FIELDS, canonical
from offline_dispatch_v3 import SIMULATED
from offline_preflight_v3 import PreflightPolicy
from offline_sandbox_v4 import limited_worker_once
from offline_worker_v3 import MAX_MESSAGE


def _simulate_limit_failure(connection, **kwargs):
    """Test a real child-process denial when OS-limit setup cannot complete."""
    with patch("offline_sandbox_v4.apply_limits", return_value=False):
        limited_worker_once(connection, **kwargs)


class V41OfflineBoundaryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.database = str(Path(tmp.name) / "one_use.sqlite")
        self.private = Ed25519PrivateKey.generate()
        self.keys = {"test-operator": self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)}
        self.policy = PreflightPolicy(frozenset({"synthetic_review"}))
        self.now = 100000
        self.request = {
            "request_id": "v41-request",
            "action": "synthetic_review",
            "plan_sha256": hashlib.sha256(b"synthetic-only").hexdigest(),
        }
        signed = dict(self.request, operator_id="test-operator",
                      nonce="v41-test-nonce-000001", expires_at=self.now + 30)
        signed["signature"] = self.private.sign(
            canonical({k: signed[k] for k in SIGNED_FIELDS})).hex()
        self.approval = signed

    def exchange(self, payload=None, *, target=limited_worker_once):
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe(duplex=True)
        process = ctx.Process(
            target=target, args=(child,),
            kwargs=dict(policy=self.policy, trusted_operator_keys=self.keys,
                        trusted_database_path=self.database, now=self.now))
        process.start()
        child.close()
        try:
            if payload is not None:
                parent.send_bytes(payload)
            self.assertTrue(parent.poll(15), "No response: treat as HOLD; child may have failed")
            raw = parent.recv_bytes(1024)
            response = json.loads(raw)
            process.join(15)
            self.assertEqual(process.exitcode, 0)
            return response
        finally:
            parent.close()
            if process.is_alive():
                process.terminate()
                process.join(5)

    def valid_message(self):
        return json.dumps({"request": self.request, "approval": self.approval}).encode()

    def test_resource_limit_initialization_failure_is_hold_without_input(self):
        response = self.exchange(target=_simulate_limit_failure)
        self.assertEqual(response, {"decision": HOLD, "simulated_effect": None})

    def test_rejected_envelope_cannot_supply_trust_keys_or_database(self):
        for injected in ({"trusted_operator_keys": {}},
                         {"trusted_database_path": ":memory:"},
                         {"now": 0}):
            with self.subTest(injected=injected):
                msg = {"request": self.request, "approval": self.approval, **injected}
                self.assertEqual(self.exchange(json.dumps(msg).encode())["decision"], HOLD)
        # Earlier rejections must not consume the valid one-use approval.
        self.assertEqual(self.exchange(self.valid_message())["decision"], SIMULATED)
        self.assertEqual(self.exchange(self.valid_message())["decision"], HOLD)

    def test_duplicate_json_fields_rejected_before_dispatch(self):
        raw = b'{"request":{},"request":{},"approval":{}}'
        self.assertEqual(self.exchange(raw)["decision"], HOLD)
        self.assertEqual(self.exchange(self.valid_message())["decision"], SIMULATED)

    def test_oversized_message_rejected_before_dispatch(self):
        raw = b"x" * (MAX_MESSAGE + 1)
        self.assertEqual(self.exchange(raw)["decision"], HOLD)
        self.assertEqual(self.exchange(self.valid_message())["decision"], SIMULATED)


if __name__ == "__main__":
    unittest.main()
