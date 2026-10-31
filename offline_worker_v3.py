"""Security V3: ONE-SHOT separate-process simulation worker.

Transport accepts bounded JSON bytes via multiprocessing.Connection.recv_bytes,
NOT pickle. Process start/configuration is trusted. Worker has no arbitrary
callable, external adapter, shell, HTTP, or physical actuator capability.
This is process separation, NOT an OS security sandbox.
"""
import json
from offline_approval_v1 import HOLD
from offline_dispatch_v3 import dispatch_simulation

MAX_MESSAGE = 16384


def _unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON field")
        result[name] = value
    return result


def _decode(raw):
    if type(raw) is not bytes or len(raw) > MAX_MESSAGE:
        raise ValueError("oversized or invalid message")
    msg = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    if type(msg) is not dict or msg.keys() != {"request", "approval"}:
        raise ValueError("unexpected envelope")
    if type(msg["request"]) is not dict or type(msg["approval"]) is not dict:
        raise ValueError("invalid contents")
    return msg


def worker_once(connection, *, policy, trusted_operator_keys,
                trusted_database_path, now):
    """Process exactly one request, enforce gate INSIDE worker, close channel.

    Only the trusted parent can set startup configuration. Never source
    trust anchors, paths or time from an untrusted message.
    """
    reply = {"decision": HOLD, "simulated_effect": None}
    try:
        raw = connection.recv_bytes(MAX_MESSAGE)
        msg = _decode(raw)
        result = dispatch_simulation(
            msg["request"], msg["approval"], policy=policy,
            trusted_operator_keys=trusted_operator_keys,
            trusted_database_path=trusted_database_path, now=now)
        reply = {"decision": result.decision, "simulated_effect": result.simulated_effect}
    except (OSError, EOFError, UnicodeError, ValueError, TypeError, KeyError,
            AttributeError, json.JSONDecodeError):
        pass  # fail closed
    finally:
        try:
            connection.send_bytes(json.dumps(reply, separators=(",", ":")).encode("utf-8"))
        except (BrokenPipeError, OSError, EOFError):
            pass
        connection.close()
