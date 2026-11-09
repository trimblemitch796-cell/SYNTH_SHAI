"""Research-branch integration regression: content verification within worker.

Synthetic local data and generated ephemeral keys only; no network or live effects.
"""
import base64
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
from offline_parent_v41 import review_offline_once


def percent_all(data):
    return b"".join(f"%{b:02X}".encode("ascii") for b in data)


class ContentBoundWorkerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = str(Path(tmp.name) / "replay.sqlite")
        self.key = Ed25519PrivateKey.generate()
        self.keys = {"human": self.key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)}
        self.policy = PreflightPolicy(frozenset({"synthetic_review"}))
        self.now = 100000
        self.idnum = 0
        self.safe = b"ordinary safe synthetic text"

    def envelope(self, canonical_payload=None, *, raw=None, encodings=(), action="synthetic_review", signature=True):
        canonical_payload = self.safe if canonical_payload is None else canonical_payload
        raw = canonical_payload if raw is None else raw
        self.idnum += 1
        request = {"request_id": f"worker-case-{self.idnum}",
                   "action": action, "plan_sha256": hashlib.sha256(canonical_payload).hexdigest()}
        signed = {**request, "operator_id": "human", "nonce": f"nonce-test-{self.idnum:016d}",
                  "expires_at": self.now + 30}
        signed["signature"] = self.key.sign(canonical({k: signed[k] for k in SIGNED_FIELDS})).hex()
        if not signature:
            signed = {}
        return {"request": request, "approval": signed,
                "content": {"raw_b64": base64.b64encode(raw).decode("ascii"),
                            "encodings": list(encodings)}}

    def run_worker(self, msg, *, through_parent=False):
        data = json.dumps(msg, separators=(",", ":")).encode("utf-8") if type(msg) is dict else msg
        kwargs = dict(policy=self.policy, trusted_operator_keys=self.keys,
                      trusted_database_path=self.db, now=self.now)
        if through_parent:
            result = review_offline_once(data, **kwargs, deadline_seconds=5)
            self.assertTrue(result.reaped, result)
            self.assertTrue(result.transport_thread_ended, result)
            return result.reply
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe(duplex=True)
        proc = ctx.Process(target=worker_once, args=(child,), kwargs=kwargs)
        proc.start()
        child.close()
        try:
            parent.send_bytes(data)
            self.assertTrue(parent.poll(10), "worker timeout")
            reply = json.loads(parent.recv_bytes(1024))
            proc.join(10)
            self.assertEqual(proc.exitcode, 0)
            return reply
        finally:
            parent.close()
            if proc.is_alive():
                proc.terminate()
                proc.join(5)

    def assert_hold(self, body, *, through_parent=False):
        self.assertEqual(self.run_worker(body, through_parent=through_parent),
                         {"decision": HOLD, "simulated_effect": None})

    def test_safe_plain_text_in_worker(self):
        self.assertEqual(self.run_worker(self.envelope()),
                         {"decision": SIMULATED, "simulated_effect": "synthetic_review_recorded"})

    def test_double_base64_in_worker(self):
        raw = base64.b64encode(base64.b64encode(self.safe))
        msg = self.envelope(raw=raw, encodings=("base64", "base64"))
        self.assertEqual(self.run_worker(msg)["decision"], SIMULATED)

    def test_percent_base64_three_layers(self):
        raw = percent_all(base64.b64encode(base64.b64encode(self.safe)))
        msg = self.envelope(raw=raw, encodings=("percent", "base64", "base64"))
        self.assertEqual(self.run_worker(msg)["decision"], SIMULATED)

    def test_encoded_sensitive_marker_rejected_in_worker(self):
        marker = b"SYNTHETIC_CONFIDENTIAL_EXAMPLE"
        raw = percent_all(base64.b64encode(base64.b64encode(marker)))
        self.assert_hold(self.envelope(marker, raw=raw, encodings=("percent", "base64", "base64")))

    def test_signed_zero_width_obfuscated_marker_holds(self):
        marker = b"SYNTHETIC_CONFIDENTIAL_EXAMPLE"
        hidden = b"SYNTHETIC_CONFIDENTIAL_\xe2\x80\x8bEXAMPLE"
        self.assert_hold(self.envelope(hidden))
        self.assert_hold(self.envelope(hidden, raw=base64.b64encode(hidden), encodings=("base64",)))

    def test_signed_compatibility_glyph_marker_holds(self):
        fullwidth = "ＳＹＮＴＨＥＴＩＣ＿ＣＯＮＦＩＤＥＮＴＩＡＬ＿ＥＸＡＭＰＬＥ".encode("utf-8")
        self.assert_hold(self.envelope(fullwidth))

    def test_control_character_holds_even_with_valid_signature(self):
        self.assert_hold(self.envelope(b"hello\x00world"))
        self.assert_hold(self.envelope("hello\u202eworld".encode("utf-8")))

    def test_safe_multiline_text_still_simulates(self):
        payload = b"safe first line\nsecond line\twith tab"
        self.assertEqual(self.run_worker(self.envelope(payload))["decision"], SIMULATED)

    def test_content_mismatch_rejected_in_worker(self):
        msg = self.envelope()
        msg["content"]["raw_b64"] = base64.b64encode(b"tampered").decode("ascii")
        self.assert_hold(msg)

    def test_missing_content_envelope_fails_closed(self):
        msg = self.envelope()
        del msg["content"]
        self.assert_hold(msg)

    def test_extra_content_field_fails_closed(self):
        msg = self.envelope()
        msg["content"]["trusted_database_path"] = ":memory:"
        self.assert_hold(msg)

    def test_unknown_encoding_fails_closed(self):
        self.assert_hold(self.envelope(encodings=("rot13",)))

    def test_wrong_depth_fails_closed(self):
        msg = self.envelope()
        msg["content"]["encodings"] = ["base64"] * 4
        self.assert_hold(msg)

    def test_ambiguous_undeclared_layer_fails_closed(self):
        self.assert_hold(self.envelope(raw=base64.b64encode(self.safe)))

    def test_invalid_signature_fails_closed(self):
        self.assert_hold(self.envelope(signature=False))

    def test_unknown_action_fails_closed(self):
        self.assert_hold(self.envelope(action="WRITE"))

    def test_replay_rejected_in_worker(self):
        msg = self.envelope()
        self.assertEqual(self.run_worker(msg)["decision"], SIMULATED)
        self.assert_hold(msg)

    def test_duplicate_json_keys_rejected(self):
        self.assert_hold(b'{"request":{},"request":{},"approval":{},"content":{}}')

    def test_oversized_envelope_rejected(self):
        self.assert_hold(b"a" * (MAX_MESSAGE + 1))

    def test_trusted_keys_cannot_arrive_in_message(self):
        msg = self.envelope()
        msg["trusted_operator_keys"] = {}
        self.assert_hold(msg)

    def test_parent_v41_rejects_encoded_marker(self):
        marker = b"SYNTHETIC_CONFIDENTIAL_EXAMPLE"
        msg = self.envelope(marker, raw=base64.b64encode(marker), encodings=("base64",))
        self.assert_hold(msg, through_parent=True)

    def test_parent_v41_valid_and_replay(self):
        msg = self.envelope()
        self.assertEqual(self.run_worker(msg, through_parent=True)["decision"], SIMULATED)
        self.assert_hold(msg, through_parent=True)

    def test_malformed_transfer_base64_rejected(self):
        msg = self.envelope()
        msg["content"]["raw_b64"] = "***INVALID***"
        self.assert_hold(msg)

    def test_legacy_envelope_does_not_consume_approval(self):
        msg = self.envelope()
        legacy = {"request": msg["request"], "approval": msg["approval"]}
        self.assert_hold(legacy)
        self.assertEqual(self.run_worker(msg)["decision"], SIMULATED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
