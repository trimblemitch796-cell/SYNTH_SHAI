"""MANIAC MONITOR SYSTEM (offline simulation only - controls no hardware).

Tracks heartbeats, a watchdog, and a fault register, and reports one
safety state using Mitch's State values from ushai_catharsis.py:

  MONITOR    - healthy: every heartbeat fresh, watchdog kicked, no faults
  144 HOLD   - something is missing, late, faulty or malformed
  SAFE_LOCK  - critical or repeating fault. LATCHED: only an explicit
               human_reset() leaves it, and that goes to HOLD (never
               straight to MONITOR). MONITOR returns only after a fresh
               full set of heartbeats and a watchdog kick.

It never grants approval: approval_granted is always False.
"""
from ushai_catharsis import State

DEFAULT_TIMEOUT = 2.0      # seconds, matches the supervisor
DEFAULT_REPEAT_LIMIT = 3   # same fault this many times -> SAFE_LOCK


class Monitor:
    approval_granted = False

    def __init__(self, clock, components, timeouts=None,
                 watchdog_timeout=DEFAULT_TIMEOUT, repeat_limit=DEFAULT_REPEAT_LIMIT):
        self.clock = clock                    # injectable: () -> float seconds
        self.timeouts = {c: DEFAULT_TIMEOUT for c in components}
        self.timeouts.update(timeouts or {})
        self.watchdog_timeout = watchdog_timeout
        self.repeat_limit = repeat_limit
        self.last_beat = {}                   # component -> time
        self.last_kick = None
        self.faults = {}                      # code -> description
        self.fault_counts = {}                # code -> times raised
        self.latched = False
        self.state = State.HOLD               # start safe until proven healthy
        self.audit = []

    # ---- inputs -------------------------------------------------
    def heartbeat(self, component):
        if component not in self.timeouts:
            return self.raise_fault("MALFORMED_INPUT", "unknown component %r" % (component,))
        self.last_beat[component] = self.clock()
        return self.evaluate()

    def kick(self):
        """Watchdog kick: the supervised loop must call this regularly."""
        self.last_kick = self.clock()
        return self.evaluate()

    def raise_fault(self, code, description="", critical=False):
        if not isinstance(code, str) or not code:
            code, description = "MALFORMED_INPUT", "bad fault code %r" % (code,)
        self.faults[code] = description
        self.fault_counts[code] = self.fault_counts.get(code, 0) + 1
        self._log("fault raised: %s %s" % (code, description))
        if critical is True or self.fault_counts[code] >= self.repeat_limit:
            self._latch("critical fault" if critical is True else "fault %s repeated" % code)
        return self.evaluate()

    def clear_fault(self, code, reason):
        if not isinstance(reason, str) or not reason.strip():
            self._log("clear refused for %s: reason required" % code)
            return self.evaluate()
        if code in self.faults:
            del self.faults[code]
            self._log("fault cleared: %s (%s)" % (code, reason))
        return self.evaluate()          # clearing never un-latches SAFE_LOCK

    def human_reset(self, operator_id, reason):
        """The only way out of SAFE_LOCK. Goes to HOLD; old heartbeats are
        forgotten so a fresh full set is needed before MONITOR."""
        ok = all(isinstance(x, str) and x.strip() for x in (operator_id, reason))
        if not ok:
            self._log("human reset refused: operator id and reason required")
            return self.evaluate()
        if self.faults:
            self._log("human reset refused: clear active faults first")
            return self.evaluate()
        self.latched = False
        self.fault_counts = {}
        self.last_beat = {}
        self.last_kick = None
        self._log("human reset by %s: %s" % (operator_id, reason))
        return self.evaluate()

    # ---- outputs ------------------------------------------------
    def evaluate(self):
        try:
            new, reason = self._decide()
        except Exception as exc:  # fail closed
            new = State.SAFE_LOCK if self.latched else State.HOLD
            reason = "internal error: %s" % type(exc).__name__
        self._set(new, reason)
        return self.state

    def snapshot(self):
        state = self.evaluate()
        return {"state": state.value, "reason": self.reason,
                "faults": sorted(self.faults), "approval_granted": False}

    # ---- internals ----------------------------------------------
    def _decide(self):
        if self.latched:
            return State.SAFE_LOCK, "SAFE_LOCK latched: human reset required"
        now = self.clock()
        if self.faults:
            return State.HOLD, "active fault(s): %s" % ", ".join(sorted(self.faults))
        for comp, limit in sorted(self.timeouts.items()):
            beat = self.last_beat.get(comp)
            if beat is None or beat > now or now - beat > limit:
                return State.HOLD, "missed heartbeat: %s" % comp
        if self.last_kick is None or self.last_kick > now or now - self.last_kick > self.watchdog_timeout:
            return State.HOLD, "watchdog not kicked"
        return State.MONITOR, "healthy"

    def _latch(self, why):
        self.latched = True
        self._log("SAFE_LOCK latched: %s" % why)

    def _set(self, new, reason):
        self.reason = reason
        if new != self.state:
            self._log("%s -> %s (%s)" % (self.state.value, new.value, reason))
            self.state = new

    def _log(self, text):
        self.audit.append(text)
