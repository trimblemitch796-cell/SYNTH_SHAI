"""Linux resource ceilings and fail-closed V4 worker, all offline."""
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
from offline_sandbox_v4 import LIMITS, apply_limits, limited_worker_once, resource


def _probe_limits(connection):
    """Test-only child: return actual OS limits and whether hard caps resist raise."""
    try:
        ok = apply_limits()
        observed = {}
        cannot_raise = True
        if ok:
            for name, cap in LIMITS:
                kind = getattr(resource, name)
                soft, hard = resource.getrlimit(kind)
                observed[name] = (soft, hard)
                if hard > cap or soft > hard:
                    ok = False
                try:
                    resource.setrlimit(kind, (hard, hard + 1))
                    cannot_raise = False
                except (ValueError, OSError):
                    pass
        connection.send({"ok": ok, "observed": observed, "cannot_raise": cannot_raise})
    finally:
        connection.close()


class LinuxResourceWorkerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = str(Path(tmp.name) / "replay.sqlite")
        self.key = Ed25519PrivateKey.generate()
        self.keys = {"human": self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)}
        self.request = {"request_id": "v4-request", "action": "synthetic_review",
                        "plan_sha256": hashlib.sha256(b"offline").hexdigest()}
        self.policy = PreflightPolicy(frozenset({"synthetic_review"}))
        self.now = 100000
        self.approval = self.sign()

    def sign(self, **changes):
        body = dict(self.request, operator_id="human",
                    nonce="unique-v4-challenge-0001", expires_at=self.now + 30)
        body.update(changes)
        body["signature"] = self.key.sign(
            canonical({k: body[k] for k in SIGNED_FIELDS})).hex()
        return body

    def start(self, target, args=(), kwargs=None, message=None):
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe(duplex=True)
        proc = ctx.Process(target=target, args=(child,) + args, kwargs=kwargs or {})
        proc.start()
        child.close()
        try:
            if message is not None:
                parent.send_bytes(message)
            self.assertTrue(parent.poll(12), "child hung; fail closed")
            if message is not None:
                result = json.loads(parent.recv_bytes(1024))
            else:
                result = parent.recv()
            proc.join(12)
            self.assertEqual(proc.exitcode, 0)
            return result
        finally:
            parent.close()
            if proc.is_alive():
                proc.terminate()
                proc.join(3)

    def call_worker(self, request=None, approval=None):
        raw = json.dumps({
            "request": self.request if request is None else request,
            "approval": self.approval if approval is None else approval
        }).encode("utf-8")
        return self.start(
            limited_worker_once,
            kwargs={"policy": self.policy, "trusted_operator_keys": self.keys,
                    "trusted_database_path": self.db, "now": self.now},
            message=raw)

    def test_linux_resource_ceiling_is_active(self):
        result = self.start(_probe_limits)
        self.assertTrue(result["ok"], result)
        for name, cap in LIMITS:
            soft, hard = result["observed"][name]
            self.assertEqual(soft, hard)
            self.assertLessEqual(hard, cap)
        self.assertTrue(result["cannot_raise"], result)

    def test_signed_approved_synthetic_operation(self):
        self.assertEqual(self.call_worker()["decision"], SIMULATED)

    def test_replay_denied_across_resource_restricted_workers(self):
        self.assertEqual(self.call_worker()["decision"], SIMULATED)
        self.assertEqual(self.call_worker()["decision"], HOLD)

    def test_forgery_rejected(self):
        tampered = dict(self.approval, signature="00" * 64)
        self.assertEqual(self.call_worker(approval=tampered)["decision"], HOLD)

    def test_forbidden_action_rejected(self):
        changed = dict(self.request, action="run_command")
        self.assertEqual(self.call_worker(request=changed,
                                          approval=self.sign(action="run_command"))["decision"], HOLD)

    def test_no_os_limit_api_fails_closed(self):
        from unittest.mock import patch
        import offline_sandbox_v4
        with patch.object(offline_sandbox_v4, "resource", None):
            self.assertFalse(offline_sandbox_v4.apply_limits())


if __name__ == "__main__":
    unittest.main()
