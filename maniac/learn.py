"""111000 COMPARE / LEARN (offline simulation only - controls no hardware).

Compares the outcome with what was expected and writes a lesson to an
append-only JSON-lines log (one JSON object per line, never rewritten).

THE RULE: learning may only make the system MORE cautious.
  - It can flag a reason pattern that keeps causing HOLDs for extra review.
  - It can tighten the tolerance / max age.
  - It can NEVER loosen a threshold or approve anything.
"""
import json

from maniac.evidence import TOLERANCE, MAX_AGE

GATE = "111000 COMPARE / LEARN"
FLAG_AFTER = 2          # same HOLD reason this many times -> flagged for review
TIGHTEN_BY = 0.8        # a flagged pattern tightens its setting to 80 %

# Which words in a reason tighten which setting
TIGHTENS = {"contradict": "tolerance", "disagree": "tolerance",
            "stale": "max_age", "heartbeat": "max_age"}


class LessonLog:
    def __init__(self, path=None):
        self.path = path            # None = keep in memory only
        self._memory = []

    def record(self, outcome, expected, observed, reasons, human_decision=None):
        """Append one lesson. Returns True if expectation matched."""
        matched = outcome == expected
        lesson = {"outcome": outcome, "expected": expected, "observed": observed,
                  "matched": matched, "reasons": [list(r) for r in reasons],
                  "human_decision": _decision_dict(human_decision)}
        line = json.dumps(lesson, sort_keys=True)
        if self.path is None:
            self._memory.append(line)
        else:
            with open(self.path, "a", encoding="utf-8") as f:   # "a" = append only
                f.write(line + "\n")
        return matched

    def lines(self):
        if self.path is None:
            return list(self._memory)
        try:
            with open(self.path, encoding="utf-8") as f:
                return [ln.rstrip("\n") for ln in f if ln.strip()]
        except FileNotFoundError:
            return []

    def flagged_patterns(self):
        """Reason texts that caused HOLD at least FLAG_AFTER times.
        A corrupt log line is itself flagged (more caution, never less)."""
        counts = {}
        for ln in self.lines():
            try:
                lesson = json.loads(ln)
                reasons = [r[1] for r in lesson["reasons"]] if lesson["outcome"] == "144 HOLD" else []
            except Exception:
                reasons = ["corrupt lesson log line"]
                counts[reasons[0]] = FLAG_AFTER - 1        # flag straight away
            for text in reasons:
                counts[text] = counts.get(text, 0) + 1
        return sorted(t for t, n in counts.items() if n >= FLAG_AFTER)

    def cautious_settings(self, tolerance=TOLERANCE, max_age=MAX_AGE):
        """Settings after learning. Each is min(current, learned) - so it can
        only stay the same or get stricter. Nothing in the log can raise it."""
        settings = {"tolerance": tolerance, "max_age": max_age}
        for pattern in self.flagged_patterns():
            for word, key in TIGHTENS.items():
                if word in pattern:
                    settings[key] = min(settings[key], settings[key] * TIGHTEN_BY)
        settings["tolerance"] = min(settings["tolerance"], tolerance)
        settings["max_age"] = min(settings["max_age"], max_age)
        settings["review_flags"] = self.flagged_patterns()
        return settings


def _decision_dict(d):
    if d is None:
        return None
    return {"operator_id": d.operator_id, "decision": d.decision, "reason": d.reason}
