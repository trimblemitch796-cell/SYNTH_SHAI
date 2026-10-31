"""Security V5 research: trusted-parent deadline on a fixed synthetic worker.

Uses ONLY the known V4 worker, never untrusted user-supplied code or handlers.
Input/output are bytes + strict JSON. Parent owns wall-clock termination.
This is NOT an OS sandbox or production execution capability.
"""
import json
import math
import multiprocessing
import time

from offline_approval_v1 import HOLD
from offline_dispatch_v3 import SIMULATED
from offline_sandbox_v4 import limited_worker_once
from offline_worker_v3 import MAX_MESSAGE

MAX_TIMEOUT_SECONDS = 10.0
DENIED = {"decision": HOLD, "simulated_effect": None}
SUCCESS = {"decision": SIMULATED, "simulated_effect": "synthetic_review_recorded"}


def _reply(raw):
    if len(raw) > 512:
        return dict(DENIED)
    try:
        response = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, TypeError):
        return dict(DENIED)
    if type(response) is not dict or response.keys() != DENIED.keys():
        return dict(DENIED)
    if response == SUCCESS:
        return dict(SUCCESS)
    return dict(DENIED)


def run_bounded_simulation(raw, *, policy, trusted_operator_keys,
                           trusted_database_path, now, deadline_seconds=3.0):
    """Return a bounded synthetic result or fail closed.

    Start configuration must originate with a trusted caller. A child timeout,
    crash, truncated reply or malformed message cannot produce a success.
    """
    if type(raw) is not bytes or len(raw) > MAX_MESSAGE:
        return dict(DENIED)
    if (type(deadline_seconds) not in (int, float)
            or not math.isfinite(deadline_seconds)
            or not 0 < deadline_seconds <= MAX_TIMEOUT_SECONDS):
        return dict(DENIED)

    parent = child = proc = None
    try:
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe(duplex=True)
        proc = ctx.Process(
            target=limited_worker_once, args=(child,),
            kwargs={"policy": policy, "trusted_operator_keys": trusted_operator_keys,
                    "trusted_database_path": trusted_database_path, "now": now})
        started = time.monotonic()
        proc.start()
        child.close()
        child = None
        parent.send_bytes(raw)
        remaining = deadline_seconds - (time.monotonic() - started)
        if remaining <= 0 or not parent.poll(remaining):
            return dict(DENIED)
        response = _reply(parent.recv_bytes(512))
        remaining = max(0.0, deadline_seconds - (time.monotonic() - started))
        proc.join(remaining)
        if proc.exitcode != 0:
            return dict(DENIED)
        return response
    except (OSError, EOFError, ValueError, TypeError, RuntimeError,
            BufferError, OverflowError):
        return dict(DENIED)
    finally:
        if parent is not None:
            parent.close()
        if child is not None:
            child.close()
        if proc is not None and proc.pid is not None:
            if proc.is_alive():
                proc.terminate()
                proc.join(1.0)
            if proc.is_alive():
                proc.kill()
                proc.join(1.0)
