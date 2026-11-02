"""Research-only parent lifecycle for the fixed V4 synthetic worker.

This is NOT a live execution controller or an OS security sandbox. The public
entry point pins the worker target; only trusted Python tests may inject a
synthetic fault target through the private test seam.
"""
from dataclasses import dataclass
import json
import multiprocessing
import threading
import time

from offline_approval_v1 import HOLD
from offline_dispatch_v3 import SIMULATED
from offline_sandbox_v4 import limited_worker_once
from offline_worker_v3 import MAX_MESSAGE

_HOLD_REPLY = {"decision": HOLD, "simulated_effect": None}
_SIM_REPLY = {"decision": SIMULATED, "simulated_effect": "synthetic_review_recorded"}


@dataclass(frozen=True)
class ParentOutcome:
    reply: dict
    reason: str
    reaped: bool
    exitcode: int | None
    transport_thread_ended: bool


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate response field")
        result[key] = value
    return result


def _decode_reply(raw):
    message = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    if type(message) is not dict or message not in (_HOLD_REPLY, _SIM_REPLY):
        raise ValueError("unexpected response")
    return message


def _exchange_with_child(*, target, payload, kwargs, deadline_seconds=3.0,
                         cleanup_grace=0.5):
    """Private fault-injection seam; target/kwargs are trusted Python values.

    The deadline covers transport and child exit AFTER Process.start returns.
    It does not guarantee Process.start, descendants or uninterruptible tasks.
    """
    if (type(payload) is not bytes or len(payload) > MAX_MESSAGE or
            not 0 < deadline_seconds <= 30 or not 0 < cleanup_grace <= 5):
        return ParentOutcome(dict(_HOLD_REPLY), "invalid_input", True, None, True)

    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe(duplex=True)
    process = ctx.Process(target=target, args=(child,), kwargs=kwargs)
    try:
        process.start()
    except Exception:
        parent.close()
        child.close()
        return ParentOutcome(dict(_HOLD_REPLY), "start_failed", True, None, True)
    child.close()
    deadline = time.monotonic() + deadline_seconds

    completed = {}

    def _transport():
        try:
            parent.send_bytes(payload)
            completed["raw"] = parent.recv_bytes(1024)
        except (EOFError, OSError, ValueError) as error:
            completed["error"] = type(error).__name__

    thread = threading.Thread(target=_transport, daemon=True, name="v41-parent-ipc")
    reason = "no_reply"
    answer = dict(_HOLD_REPLY)
    try:
        thread.start()
        thread.join(max(0, deadline - time.monotonic()))
        if thread.is_alive():
            reason = "transport_timeout"
        elif "error" in completed:
            reason = "transport_" + completed["error"]
        elif "raw" not in completed:
            reason = "no_reply"
        else:
            process.join(max(0, deadline - time.monotonic()))
            if process.exitcode is None:
                reason = "exit_timeout"
            elif process.exitcode != 0:
                reason = "abnormal_exit"
            else:
                try:
                    answer = _decode_reply(completed["raw"])
                    reason = "clean_exit_and_valid_reply"
                except (ValueError, UnicodeError, TypeError) as error:
                    reason = "invalid_reply_" + type(error).__name__
    except Exception:
        answer = dict(_HOLD_REPLY)
        reason = "parent_error"
    finally:
        if process.is_alive():
            process.terminate()
            process.join(cleanup_grace)
        if process.is_alive():
            process.kill()
            process.join(cleanup_grace)
        parent.close()
        if thread.ident is not None:
            thread.join(cleanup_grace)

    reaped = process.exitcode is not None
    transport_ended = not thread.is_alive()
    if not reaped or not transport_ended:
        answer = dict(_HOLD_REPLY)
        reason = "cleanup_incomplete"
    return ParentOutcome(answer, reason, reaped, process.exitcode, transport_ended)


def review_offline_once(payload, *, policy, trusted_operator_keys,
                        trusted_database_path, now, deadline_seconds=3.0,
                        cleanup_grace=0.5):
    """Run only the pinned V4 synthetic review worker, with no live effect."""
    return _exchange_with_child(
        target=limited_worker_once, payload=payload,
        kwargs={"policy": policy, "trusted_operator_keys": trusted_operator_keys,
                "trusted_database_path": trusted_database_path, "now": now},
        deadline_seconds=deadline_seconds, cleanup_grace=cleanup_grace)
