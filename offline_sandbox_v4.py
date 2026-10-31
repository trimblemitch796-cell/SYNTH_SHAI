"""Security V4 foundation: Linux OS-enforced resource ceilings for a one-shot worker.

This controls resource use only. It does NOT isolate files, processes,
credentials, sockets, networks or OS privileges and is NOT a security sandbox.
No real-world operation or arbitrary callable is accepted.
"""
import json
import sys

from offline_approval_v1 import HOLD
from offline_worker_v3 import worker_once

try:
    import resource
except ImportError:  # fail closed on hosts without the required OS API
    resource = None

# Fixed policy: never accept limits from an untrusted message.
LIMITS = (
    ("RLIMIT_CPU", 5),
    ("RLIMIT_AS", 512 * 1024 * 1024),
    ("RLIMIT_FSIZE", 8 * 1024 * 1024),
    ("RLIMIT_NOFILE", 64),
)


def apply_limits():
    """Set both soft and hard Linux rlimits; return False on any failure."""
    if not sys.platform.startswith("linux") or resource is None:
        return False
    try:
        for name, cap in LIMITS:
            kind = getattr(resource, name)
            soft, hard = resource.getrlimit(kind)
            # If host already restricts below a cap, preserve tighter policy.
            candidate = min(cap, soft if soft != resource.RLIM_INFINITY else cap,
                            hard if hard != resource.RLIM_INFINITY else cap)
            if candidate <= 0:
                return False
            resource.setrlimit(kind, (candidate, candidate))
        return True
    except (ValueError, OSError, AttributeError):
        return False


def limited_worker_once(connection, *, policy, trusted_operator_keys,
                        trusted_database_path, now):
    """Apply OS ceilings before handling JSON and checking signed approval."""
    if not apply_limits():
        try:
            connection.send_bytes(json.dumps(
                {"decision": HOLD, "simulated_effect": None}).encode("utf-8"))
        except (OSError, EOFError, BrokenPipeError):
            pass
        finally:
            connection.close()
        return
    worker_once(
        connection, policy=policy, trusted_operator_keys=trusted_operator_keys,
        trusted_database_path=trusted_database_path, now=now)
