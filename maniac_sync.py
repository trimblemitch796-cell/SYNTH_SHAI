"""
SYNTH_SHAI / USHAI
MANIAC_SYNC_V1

Offline synchronization and safety supervisor.

111000 - LEARN
144    - HOLD
444000 - VERIFY

Simulation only.
No physical actuation.
No autonomous authorization.
"""

import hashlib
import json
import time
from dataclasses import dataclass


HOLD = "HOLD"
MONITOR = "MONITOR"
SAFE_LOCK = "SAFE_LOCK"

ALLOWED_STATES = {HOLD, MONITOR, SAFE_LOCK}


@dataclass
class SyncMessage:
    source: str
    sequence: int
    timestamp: float
    state: str
    checksum: str = ""

    def payload(self):
        return {
            "source": self.source,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "state": self.state,
        }

    def calculate_checksum(self):
        data = json.dumps(
            self.payload(),
            sort_keys=True
        ).encode()

        return hashlib.sha256(data).hexdigest()

    def seal(self):
        self.checksum = self.calculate_checksum()
        return self

    def valid(self):
        return self.checksum == self.calculate_checksum()


class ManiacSync:

    def __init__(self, timeout=5.0):
        self.timeout = timeout
        self.state = HOLD
        self.last_sequence = {}
        self.last_heartbeat = {}
        self.component_states = {}
        self.audit_log = []
        self.physical_actuation = False

    def log(self, event):
        self.audit_log.append({
            "time": time.time(),
            "event": event,
            "state": self.state,
        })

    def enter_hold(self, reason):
        self.state = HOLD
        self.log("144 HOLD: " + reason)
        return False

    def receive(self, message):
        now = time.time()

        if not message.valid():
            return self.enter_hold(
                "Corrupted message"
            )

        if message.state not in ALLOWED_STATES:
            return self.enter_hold(
                "Invalid state"
            )

        if message.timestamp > now + 1:
            return self.enter_hold(
                "Future timestamp"
            )

        if now - message.timestamp > self.timeout:
            return self.enter_hold(
                "Delayed message"
            )

        previous = self.last_sequence.get(
            message.source, -1
        )

        if message.sequence <= previous:
            return self.enter_hold(
                "Duplicate or replayed message"
            )

        self.last_sequence[message.source] = (
            message.sequence
        )

        self.last_heartbeat[message.source] = now

        self.component_states[message.source] = (
            message.state
        )

        if len(set(self.component_states.values())) > 1:
            return self.enter_hold(
                "Conflicting component states"
            )

        self.log(
            "Verified message from " + message.source
        )

        return True

    def check_heartbeats(self):
        now = time.time()

        required = {"SYNTH_SHAI", "USHAI"}

        if not required.issubset(
            self.last_heartbeat.keys()
        ):
            return self.enter_hold(
                "Missing required heartbeat"
            )

        for source in required:
            last = self.last_heartbeat[source]

            if now - last > self.timeout:
                return self.enter_hold(
                    "Lost heartbeat: " + source
                )

        return True

    def request_recovery(self, human_approved=False):
        if not human_approved:
            return self.enter_hold(
                "Unauthorized recovery"
            )

        if not self.check_heartbeats():
            return False

        required = {"SYNTH_SHAI", "USHAI"}

        for source in required:
            if self.component_states.get(source) != HOLD:
                return self.enter_hold(
                    "Recovery state disagreement"
                )

        self.state = MONITOR

        self.log(
            "444000: Human-approved simulation recovery"
        )

        return True

    def safe_shutdown(self):
        self.state = SAFE_LOCK
        self.physical_actuation = False
        self.log("Safe shutdown")
        return True


if __name__ == "__main__":

    supervisor = ManiacSync()

    print("MANIAC_SYNC_V1")
    print("Initial state:", supervisor.state)

    for source in ("SYNTH_SHAI", "USHAI"):
        message = SyncMessage(
            source=source,
            sequence=1,
            timestamp=time.time(),
            state=HOLD,
        ).seal()

        supervisor.receive(message)

    print(
        "Heartbeat verification:",
        supervisor.check_heartbeats()
    )

    print(
        "Unauthorized recovery:",
        supervisor.request_recovery(False)
    )

    print("Final state:", supervisor.state)

    print(
        "Physical actuation:",
        supervisor.physical_actuation
    )

    print("Audit log:")
    for entry in supervisor.audit_log:
        print(entry)
