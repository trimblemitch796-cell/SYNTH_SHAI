import unittest
from dataclasses import replace
from maniac_sync_v1_2 import *

K = {"SYNTH_SHAI": b"a"*32, "USHAI": b"b"*32}
A = b"c"*32

class Tests(unittest.TestCase):
    def setUp(self):
        self.t = 1000.0
        self.s = Supervisor(K, A, clock=lambda: self.t)
        self.seq = {x: 0 for x in SOURCES}
    def tick(self, delta=0.1):
        self.t += delta
    def send(self, src="SYNTH_SHAI"):
        self.seq[src] += 1
        return self.s.receive(Message.sign(src, self.seq[src], self.t, HOLD, K[src]))
    def both(self):
        self.assertTrue(self.send("SYNTH_SHAI"))
        self.assertTrue(self.send("USHAI"))
    def approval(self, c):
        return Approval.sign(c["fault_id"], c["challenge"], c["issued_at"], self.t+30, A)
    def test_initial_hold(self):
        self.assertTrue(self.s.latched)
        self.assertEqual(self.s.state,HOLD)
        self.assertFalse(self.s.physical_actuation)
    def test_fresh_health(self):
        self.both()
        self.assertTrue(self.s.health_ok())
    def test_no_challenge_without_evidence(self):
        self.assertIsNone(self.s.request_challenge())
    def test_recovery_with_current_fault_approval(self):
        self.both()
        c=self.s.request_challenge()
        self.assertTrue(self.s.recover(self.approval(c)))
        self.assertEqual(self.s.state, MONITOR)
        self.assertFalse(self.s.physical_actuation)
    def test_pre_fault_approval_rejected(self):
        self.both()
        old=self.approval(self.s.request_challenge())
        self.s.hold("injected fault")
        self.tick()
        self.both()
        self.assertIsNotNone(self.s.request_challenge())
        self.assertFalse(self.s.recover(old))
        self.assertEqual(self.s.state,HOLD)
        self.assertTrue(self.s.latched)
    def test_old_heartbeat_not_sufficient(self):
        self.both()
        self.s.hold("new fault")
        self.assertIsNone(self.s.request_challenge())
    def test_unauthenticated_message_rejected(self):
        bad=Message.sign("SYNTH_SHAI",1,self.t,HOLD,b"wrong"*8)
        self.assertFalse(self.s.receive(bad))
    def test_replay_rejected(self):
        m=Message.sign("USHAI",1,self.t,HOLD,K["USHAI"])
        self.assertTrue(self.s.receive(m))
        self.assertFalse(self.s.receive(m))
    def test_expired_heartbeat(self):
        self.both()
        self.tick(6)
        self.assertIsNone(self.s.request_challenge())
    def test_expired_approval(self):
        self.both()
        c=self.s.request_challenge()
        a=Approval.sign(c["fault_id"],c["challenge"],c["issued_at"],self.t+1,A)
        self.tick(2)
        self.assertFalse(self.s.recover(a))
    def test_cross_fault_challenge(self):
        self.both()
        c=self.s.request_challenge()
        a=self.approval(c)
        self.s.hold("fault")
        self.tick()
        self.both()
        self.s.request_challenge()
        self.assertFalse(self.s.recover(a))
    def test_untrusted_approval(self):
        self.both()
        c=self.s.request_challenge()
        a=Approval.sign(c["fault_id"],c["challenge"],c["issued_at"],self.t+30,b"d"*32)
        self.assertFalse(self.s.recover(a))
    def test_conflicting_state(self):
        m=Message.sign("USHAI",1,self.t,MONITOR,K["USHAI"])
        self.assertFalse(self.s.receive(m))
    def test_old_message_after_fault(self):
        m=Message.sign("USHAI",1,self.t,HOLD,K["USHAI"])
        self.tick()
        self.s.hold("fault")
        self.assertFalse(self.s.receive(m))
    def test_missing_source(self):
        self.send()
        self.assertFalse(self.s.health_ok())
    def test_shutdown(self):
        self.s.shutdown()
        self.assertEqual(self.s.state,SAFE_LOCK)
        self.assertTrue(self.s.latched)
    def test_replay_approval(self):
        self.both()
        c=self.s.request_challenge()
        a=self.approval(c)
        self.assertTrue(self.s.recover(a))
        self.assertFalse(self.s.recover(a))
    def test_tampered_approval(self):
        self.both()
        c=self.s.request_challenge()
        a=replace(self.approval(c), fault_id="fake")
        self.assertFalse(self.s.recover(a))
if __name__ == "__main__":
    unittest.main(verbosity=2)
