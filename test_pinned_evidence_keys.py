"""Fix: trusted evidence keys and challenges are pinned OUTSIDE the envelope.

Before: shai_v31_bridge.evaluate() took trusted_keys / expected_sha256 /
expected_challenge from inside the envelope, so self-signed evidence with a
self-chosen challenge passed. Now the verifier holds all three.
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import test_shai_v31_bridge as bridge_tests
from maniac.evidence import make_bridge_checker
from shai_v31_bridge import evaluate, TrustConfig, load_trust_config
from verification_v3 import HOLD, REVIEW_REQUIRED


class PinnedKeyTests(unittest.TestCase):
    def setUp(self):
        bridge_tests.BridgeTests.setUp(self)
        self.attacker = [Ed25519PrivateKey.generate() for _ in range(2)]
        self.checker = make_bridge_checker(self.db, self.trust)

    def sign(self, challenge, keys=None):
        return bridge_tests.BridgeTests.envelope_for(self, challenge, keys)

    def attacker_trusted(self):
        out = {}
        for i, k in enumerate(self.attacker):
            pub = k.public_key().public_bytes(encoding=serialization.Encoding.Raw,
                                              format=serialization.PublicFormat.Raw)
            out["key-%d" % i] = {"source_id": "source-%d" % i, "public_key_hex": pub.hex()}
        return out

    def via_checker(self, envelope):
        return self.checker({"envelope": envelope})

    # --- the probe -----------------------------------------------------------
    def test_self_made_keys_and_self_made_challenge_hold(self):
        env = self.sign("attacker-chosen-challenge-0001", self.attacker)
        self.assertNotEqual(self.via_checker(env), REVIEW_REQUIRED)
        self.assertEqual(evaluate(env, db_path=self.db, trust=self.trust,
                                  expected_challenge="attacker-chosen-challenge-0001",
                                  expected_sha256=self.digest), HOLD)

    def test_self_made_keys_over_issued_challenge_hold(self):
        env = self.sign(self.checker.issue_challenge(self.digest), self.attacker)
        self.assertEqual(self.via_checker(env), HOLD)

    def test_envelope_supplied_trusted_keys_are_refused(self):
        challenge = self.checker.issue_challenge(self.digest)
        env = self.sign(challenge, self.attacker)
        env.update(trusted_keys=self.attacker_trusted(), expected_sha256=self.digest,
                   expected_challenge=challenge)                      # the old envelope shape
        self.assertEqual(self.via_checker(env), HOLD)
        legit = self.sign(self.checker.issue_challenge(self.digest))
        legit["trusted_keys"] = copy.deepcopy(self.trusted)          # even matching keys
        self.assertEqual(self.via_checker(legit), HOLD)

    # --- legitimate evidence still works --------------------------------------
    def test_pinned_keys_and_verifier_challenge_pass(self):
        env = self.sign(self.checker.issue_challenge(self.digest))
        self.assertEqual(self.via_checker(env), REVIEW_REQUIRED)

    def test_reused_challenge_holds(self):
        env = self.sign(self.checker.issue_challenge(self.digest))
        self.assertEqual(self.via_checker(env), REVIEW_REQUIRED)
        self.assertNotEqual(self.via_checker(copy.deepcopy(env)), REVIEW_REQUIRED)
        # Even straight to the bridge, the replay database refuses it
        self.assertEqual(evaluate(env, db_path=self.db, trust=self.trust,
                                  expected_challenge=env["record"]["challenge"],
                                  expected_sha256=self.digest), HOLD)

    def test_unissued_challenge_holds_even_with_pinned_keys(self):
        env = self.sign("never-issued-by-verifier-0001")
        self.assertNotEqual(self.via_checker(env), REVIEW_REQUIRED)

    def test_wrong_expected_hash_holds(self):
        challenge = self.checker.issue_challenge("b" * 64)    # verifier expects another report
        self.assertNotEqual(self.via_checker(self.sign(challenge)), REVIEW_REQUIRED)

    # --- missing trust -----------------------------------------------------
    def test_missing_trust_config_holds(self):
        env = self.sign(self.challenge)
        for trust in (None, self.trusted, "keys"):
            with self.subTest(trust=type(trust).__name__):
                self.assertEqual(evaluate(env, db_path=self.db, trust=trust,
                                          expected_challenge=self.challenge,
                                          expected_sha256=self.digest), HOLD)
        self.assertEqual(evaluate(env, db_path=self.db, trust=self.trust), HOLD)  # no challenge/hash
        no_trust = make_bridge_checker(self.db)
        self.assertNotEqual(no_trust({"envelope": env}), REVIEW_REQUIRED)

    def test_trust_config_is_read_only_copy(self):
        raw = copy.deepcopy(self.trusted)
        trust = TrustConfig(raw)
        raw["key-0"]["public_key_hex"] = "0" * 64              # caller edits afterwards
        env = self.sign(self.challenge)
        self.assertEqual(evaluate(env, db_path=self.db, trust=trust, expected_challenge=self.challenge,
                                  expected_sha256=self.digest), REVIEW_REQUIRED)
        with self.assertRaises(AttributeError):
            trust._raw = {}

    def test_cli_uses_trust_config_file(self):
        folder = Path(self.tmp.name)
        (folder / "trust.json").write_text(json.dumps({"trusted_keys": self.trusted}))
        self.assertIsInstance(load_trust_config(folder / "trust.json"), TrustConfig)
        (folder / "env.json").write_text(json.dumps(self.sign(self.challenge)))

        def run(trust_file):
            return subprocess.run(
                [sys.executable, "shai_v31_bridge.py", "--input", str(folder / "env.json"),
                 "--replay-db", str(folder / "cli.sqlite"), "--trust-config", str(trust_file),
                 "--challenge", self.challenge, "--expected-sha256", self.digest],
                capture_output=True, text=True, timeout=15, cwd=Path(__file__).resolve().parent)
        (folder / "attacker.json").write_text(json.dumps({"trusted_keys": self.attacker_trusted()}))
        self.assertEqual(json.loads(run(folder / "attacker.json").stdout)["decision"], HOLD)
        ok = run(folder / "trust.json")
        self.assertEqual((ok.returncode, json.loads(ok.stdout)["decision"]), (0, REVIEW_REQUIRED))
        self.assertEqual(json.loads(run(folder / "trust.json").stdout)["decision"], HOLD)   # replay


if __name__ == "__main__":
    unittest.main()
