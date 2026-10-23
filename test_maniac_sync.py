"""
SYNTH_SHAI / USHAI
MANIAC_SYNC_V1 — Offline verification tests

111000 LEARN
144 HOLD
444000 VERIFY

Simulation only. No physical hardware.
"""

import time
import unittest

from maniac_sync import (
    ManiacSync,
    SyncMessage,
    HOLD,
    MONITOR,
    SAFE_LOCK,
)


class TestManiacSync(unittest.TestCase):

    def setUp(self):
        self.system = ManiacSync(timeout=5.0)

    def message(self, source="SYNTH_SHAI",
                sequence=1, state=HOLD,
                age=0):
        return SyncMessage(
            source=source,
            sequence=sequence,
            timestamp=time.time() - age,
            state=state,
        ).seal()

    def connect_both(self):
        self.assertTrue(
            self.system.receive(
                self.message("SYNTH_SHAI")
            )
        )
        self.assertTrue(
            self.system.receive(
                self.message("USHAI")
            )
        )

    def test_01_initial_hold(self):
        self.assertEqual(self.system.state, HOLD)
        self.assertFalse(
            self.system.physical_actuation
        )

    def test_02_valid_messages(self):
        self.connect_both()
        self.assertTrue(
            self.system.check_heartbeats()
        )
        self.assertEqual(self.system.state, HOLD)

    def test_03_missing_heartbeat(self):
        self.assertFalse(
            self.system.check_heartbeats()
        )
        self.assertEqual(self.system.state, HOLD)

    def test_04_lost_heartbeat(self):
        self.connect_both()
        self.system.last_heartbeat["USHAI"] -= 10
        self.assertFalse(
            self.system.check_heartbeats()
        )
        self.assertEqual(self.system.state, HOLD)

    def test_05_delayed_message(self):
        msg = self.message(age=10)
        self.assertFalse(
            self.system.receive(msg)
        )
        self.assertEqual(self.system.state, HOLD)

    def test_06_duplicate_message(self):
        msg = self.message()
        self.assertTrue(self.system.receive(msg))
        self.assertFalse(self.system.receive(msg))
        self.assertEqual(self.system.state, HOLD)

    def test_07_corrupted_message(self):
        msg = self.message()
        msg.state = MONITOR
        self.assertFalse(self.system.receive(msg))
        self.assertEqual(self.system.state, HOLD)

    def test_08_conflicting_states(self):
        self.assertTrue(
            self.system.receive(
                self.message("SYNTH_SHAI")
            )
        )
        self.assertFalse(
            self.system.receive(
                self.message(
                    "USHAI", state=MONITOR
                )
            )
        )
        self.assertEqual(self.system.state, HOLD)

    def test_09_unauthorized_recovery(self):
        self.connect_both()
        self.assertFalse(
            self.system.request_recovery(False)
        )
        self.assertEqual(self.system.state, HOLD)

    def test_10_simulated_approved_recovery(self):
        self.connect_both()
        self.assertTrue(
            self.system.request_recovery(True)
        )
        self.assertEqual(
            self.system.state, MONITOR
        )
        self.assertFalse(
            self.system.physical_actuation
        )

    def test_11_simultaneous_failures(self):
        self.connect_both()
        self.system.last_heartbeat[
            "SYNTH_SHAI"
        ] -= 10
        self.system.last_heartbeat[
            "USHAI"
        ] -= 10
        self.assertFalse(
            self.system.check_heartbeats()
        )
        self.assertEqual(self.system.state, HOLD)

    def test_12_safe_shutdown(self):
        self.system.safe_shutdown()
        self.assertEqual(
            self.system.state, SAFE_LOCK
        )
        self.assertFalse(
            self.system.physical_actuation
        )

    def test_13_future_timestamp(self):
        msg = self.message(age=-10)
        self.assertFalse(self.system.receive(msg))
        self.assertEqual(self.system.state, HOLD)

    def test_14_invalid_state(self):
        msg = self.message(state="UNKNOWN")
        self.assertFalse(self.system.receive(msg))
        self.assertEqual(self.system.state, HOLD)

    def test_15_replay_sequence(self):
        self.assertTrue(
            self.system.receive(
                self.message(sequence=2)
            )
        )
        self.assertFalse(
            self.system.receive(
                self.message(sequence=1)
            )
        )
        self.assertEqual(self.system.state, HOLD)

    def test_16_recovery_requires_agreement(self):
        self.connect_both()
        self.system.component_states[
            "USHAI"
        ] = MONITOR
        self.assertFalse(
            self.system.request_recovery(True)
        )
        self.assertEqual(self.system.state, HOLD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
                  
