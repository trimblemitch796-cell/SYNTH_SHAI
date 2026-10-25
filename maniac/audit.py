"""999000 AUDIT - a tamper-evident hash chain (offline, no hardware).

Every entry stores the hash of the entry before it. Changing, deleting or
re-ordering any entry breaks the chain, and verify_chain() notices.
"""
import hashlib
import json

GATE = "999000 AUDIT"
GENESIS = "0" * 64


def _hash(entry):
    body = {k: entry[k] for k in ("index", "gate", "outcome", "detail", "prev")}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


class AuditChain:
    def __init__(self):
        self.entries = []

    @property
    def head(self):
        return self.entries[-1]["hash"] if self.entries else GENESIS

    def append(self, gate, outcome, detail=""):
        entry = {"index": len(self.entries), "gate": str(gate), "outcome": str(outcome),
                 "detail": str(detail), "prev": self.head}
        entry["hash"] = _hash(entry)
        self.entries.append(entry)
        return entry["hash"]


def verify_chain(entries):
    """True only if no entry was edited, deleted or re-ordered."""
    try:
        prev = GENESIS
        for i, e in enumerate(entries):
            if e["index"] != i or e["prev"] != prev or e["hash"] != _hash(e):
                return False
            prev = e["hash"]
        return True
    except Exception:  # malformed entries fail closed
        return False
