"""V4.1 offline boundary regression checks; NOT sandbox validation or an audit."""
import base64
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
        # The V0.1 worker now requires an exact, content-bound envelope.
        # The SHA-256 of decoded text must equal the signed plan_sha256.
        return json.dumps({
            "request": self.request,
            "approval": self.approval,
            "content": {
                "raw_b64": base64.b64encode(b"synthetic-only").decode("ascii"),
                "encodings": [],
            },
        }).encode()

    # 111000 / 222000 / 333 / 33300 / 555 / 555000 / 444000 / 777000
    # These are human-readable test stages, NEVER trusted authorization fields.
    # Test credentials below are ephemeral and must not be used outside this suite.

    def test_symbolic_verification_codes_do_not_grant_execution(self):
        codes = b"111000-222000-333-33300-555-555000-444000/777000"
        forged = json.loads(self.valid_message())
        forged["content"]["raw_b64"] = base64.b64encode(codes).decode("ascii")
        forged["request"]["action"] = "run_command"
        forged["approval"] = {"symbolic_code": codes.decode("ascii")}
        self.assertEqual(self.exchange(json.dumps(forged).encode()),
                         {"decision": HOLD, "simulated_effect": None})
        # A rejected symbolic request must not consume the genuine one-use approval.
        self.assertEqual(self.exchange(self.valid_message())["decision"], SIMULATED)
        self.assertEqual(self.exchange(self.valid_message())["decision"], HOLD)

    def test_declared_nested_encoding_remains_bound_and_single_use(self):
        text = b"synthetic-only"
        double_base64 = base64.b64encode(base64.b64encode(text))
        msg = json.loads(self.valid_message())
        msg["content"] = {"raw_b64": base64.b64encode(double_base64).decode("ascii"),
                          "encodings": ["base64", "base64"]}
        payload = json.dumps(msg).encode()
        self.assertEqual(self.exchange(payload)["decision"], SIMULATED)
        self.assertEqual(self.exchange(payload)["decision"], HOLD)

    def test_invalid_encoded_content_cannot_consume_valid_signature(self):
        good = json.loads(self.valid_message())
        bad_cases = []
        no_content = dict(good)
        no_content.pop("content")
        bad_cases.append(no_content)
        for payload, chain in (
            (b"changed-canonical-text", []),
            (base64.b64encode(b"synthetic-only"), []),
            (base64.b64encode(b"synthetic-only"), ["percent"]),
            (b"synthetic-only", ["base64", "base64", "base64", "base64"]),
        ):
            bad = json.loads(self.valid_message())
            bad["content"] = {
                "raw_b64": base64.b64encode(payload).decode("ascii"),
                "encodings": chain,
            }
            bad_cases.append(bad)
        malformed_transfer = json.loads(self.valid_message())
        malformed_transfer["content"]["raw_b64"] = "not!canonical!base64"
        bad_cases.append(malformed_transfer)
        for i, candidate in enumerate(bad_cases):
            with self.subTest(case=i):
                self.assertEqual(self.exchange(json.dumps(candidate).encode()),
                                 {"decision": HOLD, "simulated_effect": None})
        # The same exact authorized request still validates only once afterward.
        self.assertEqual(self.exchange(self.valid_message())["decision"], SIMULATED)
        self.assertEqual(self.exchange(self.valid_message())["decision"], HOLD)

    def test_validly_signed_encoded_synthetic_marker_is_held(self):
        # Test a blocked payload even when the SHA-256 and Ed25519 signature match.
        sensitive = b"SYNTHETIC_CONFIDENTIAL_EXAMPLE"
        request = dict(self.request, request_id="v41-marker-only",
                       plan_sha256=hashlib.sha256(sensitive).hexdigest())
        signed = dict(request, operator_id="test-operator",
                      nonce="v41-marker-nonce-000002", expires_at=self.now + 30)
        signed["signature"] = self.private.sign(
            canonical({k: signed[k] for k in SIGNED_FIELDS})).hex()
        twice = base64.b64encode(base64.b64encode(sensitive))
        encoded = {
            "request": request,
            "approval": signed,
            "content": {"raw_b64": base64.b64encode(twice).decode("ascii"),
                        "encodings": ["base64", "base64"]},
        }
        self.assertEqual(self.exchange(json.dumps(encoded).encode()),
                         {"decision": HOLD, "simulated_effect": None})

    def test_resource_limit_initialization_failure_is_hold_without_input(self):
        response = self.exchange(target=_simulate_limit_failure)
        self.assertEqual(response, {"decision": HOLD, "simulated_effect": None})

    def test_rejected_envelope_cannot_supply_trust_keys_or_database(self):
        for injected in ({"trusted_operator_keys": {}},
                         {"trusted_database_path": ":memory:"},
                         {"now": 0}):
            with self.subTest(injected=injected):
                msg = json.loads(self.valid_message())
                msg.update(injected)
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
