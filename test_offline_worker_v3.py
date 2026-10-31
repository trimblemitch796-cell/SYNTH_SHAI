"""Separate-process, byte-only, single-request adversarial evaluation."""
import hashlib
import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from offline_approval_v1 import HOLD, SIGNED_FIELDS, canonical
from offline_dispatch_v3 import SIMULATED
from offline_preflight_v3 import PreflightPolicy
from offline_worker_v3 import MAX_MESSAGE, worker_once


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "approval.sqlite")
        self.key = Ed25519PrivateKey.generate()
        public = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        self.keys = {"trusted-human": public}
        self.request = {"request_id": "req-1", "action": "synthetic_review",
                        "plan_sha256": hashlib.sha256(b"review").hexdigest()}
        self.now = 100000
        self.policy = PreflightPolicy(frozenset({"synthetic_review"}))
        self.approval = self.sign()

    def sign(self, **updates):
        signed = dict(self.request, operator_id="trusted-human",
                      nonce="nonce-unique-001234", expires_at=self.now + 60)
        signed.update(updates)
        signed["signature"] = self.key.sign(
            canonical({k: signed[k] for k in SIGNED_FIELDS})).hex()
        return signed

    def exchange(self, raw):
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe(duplex=True)
        proc = ctx.Process(
            target=worker_once, args=(child,),
            kwargs=dict(policy=self.policy, trusted_operator_keys=self.keys,
                        trusted_database_path=self.db, now=self.now))
        proc.start()
        child.close()
        try:
            parent.send_bytes(raw)
            self.assertTrue(parent.poll(10), "worker timeout: fail closed")
            response = json.loads(parent.recv_bytes(1024))
            proc.join(10)
            self.assertEqual(proc.exitcode, 0)
            return response
        finally:
            parent.close()
            if proc.is_alive():
                proc.terminate()
                proc.join(5)

    def transmit(self, request=None, approval=None):
        body = {"request": self.request if request is None else request,
                "approval": self.approval if approval is None else approval}
        return self.exchange(json.dumps(body).encode("utf-8"))

    def test_signed_request_runs_only_simulated_effect(self):
        self.assertEqual(self.transmit(),
                         {"decision": SIMULATED, "simulated_effect": "synthetic_review_recorded"})

    def test_replay_denied_across_fresh_processes(self):
        self.assertEqual(self.transmit()["decision"], SIMULATED)
        self.assertEqual(self.transmit()["decision"], HOLD)

    def test_same_request_different_nonce_denied_across_processes(self):
        self.assertEqual(self.transmit()["decision"], SIMULATED)
        self.assertEqual(self.transmit(approval=self.sign(nonce="nonce-unique-009999"))["decision"], HOLD)

    def test_invalid_signature_denied(self):
        forged = dict(self.approval, signature="00" * 64)
        self.assertEqual(self.transmit(approval=forged)["decision"], HOLD)

    def test_unapproved_action_denied(self):
        request = dict(self.request, action="transfer_funds")
        self.assertEqual(self.transmit(request=request, approval=self.sign(action="transfer_funds"))["decision"], HOLD)

    def test_untrusted_envelope_cannot_supply_keys(self):
        body = {"request": self.request, "approval": self.approval, "trusted_operator_keys": {}}
        self.assertEqual(self.exchange(json.dumps(body).encode())["decision"], HOLD)
        self.assertEqual(self.transmit()["decision"], SIMULATED)

    def test_untrusted_envelope_cannot_supply_db(self):
        body = {"request": self.request, "approval": self.approval, "trusted_database_path": ":memory:"}
        self.assertEqual(self.exchange(json.dumps(body).encode())["decision"], HOLD)
        self.assertEqual(self.transmit()["decision"], SIMULATED)

    def test_untrusted_envelope_cannot_supply_now(self):
        body = {"request": self.request, "approval": self.approval, "now": 0}
        self.assertEqual(self.exchange(json.dumps(body).encode())["decision"], HOLD)

    def test_duplicate_json_keys_denied(self):
        raw = ('{"request":{},"request":{},"approval":{}}').encode()
        self.assertEqual(self.exchange(raw)["decision"], HOLD)

    def test_oversized_payload_denied(self):
        self.assertEqual(self.exchange(b"x" * (MAX_MESSAGE + 1))["decision"], HOLD)

    def test_malformed_json_denied(self):
        self.assertEqual(self.exchange(b'{"request":')["decision"], HOLD)

    def test_nonobject_json_denied(self):
        self.assertEqual(self.exchange(b"[]")["decision"], HOLD)

    def test_python_callback_cannot_cross_json_boundary(self):
        callback = object()
        with self.assertRaises(TypeError):
            json.dumps({"request": self.request, "approval": self.approval, "callback": callback})

    def test_worker_one_shot_enforced_by_pipe_closure(self):
        self.assertEqual(self.transmit()["decision"], SIMULATED)
        self.assertEqual(self.transmit()["decision"], HOLD)


if __name__ == "__main__":
    unittest.main()
