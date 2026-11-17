"""Strict content-bound, one-shot offline synthetic review worker (research branch).

Only canonical UTF-8 text committed by a one-use signed plan digest is eligible
for the fixed synthetic effect. No live execution, network, arbitrary callback
or filesystem mutation beyond the trusted local replay store. Not a sandbox.

Experimental, intentionally incompatible input envelope: old envelopes lacking
`content` fail closed. No legacy unsigned/bypass entrypoint is provided here.
"""
import base64
import binascii
import json

from offline_approval_v1 import HOLD
from offline_dispatch_v3 import SIMULATED
from research_content_binding_v01 import MAX_RAW_BYTES, guarded_synthetic_review

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
    if type(msg) is not dict or msg.keys() != {"request", "approval", "content"}:
        raise ValueError("unexpected envelope")
    if type(msg["request"]) is not dict or type(msg["approval"]) is not dict:
        raise ValueError("invalid contents")
    content = msg["content"]
    if type(content) is not dict or content.keys() != {"raw_b64", "encodings"}:
        raise ValueError("invalid content envelope")
    raw_b64, chain = content["raw_b64"], content["encodings"]
    if type(raw_b64) is not str or not 0 < len(raw_b64) <= MAX_MESSAGE:
        raise ValueError("invalid content field")
    if type(chain) is not list or len(chain) > 3 or any(
            type(item) is not str or item not in ("base64", "percent") for item in chain):
        raise ValueError("invalid encoding chain")
    try:
        raw_payload = base64.b64decode(raw_b64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("invalid payload transfer encoding") from exc
    if len(raw_payload) == 0 or len(raw_payload) > MAX_RAW_BYTES or base64.b64encode(raw_payload).decode("ascii") != raw_b64:
        raise ValueError("noncanonical or oversized transfer encoding")
    return msg["request"], msg["approval"], raw_payload, tuple(chain)


def worker_once(connection, *, policy, trusted_operator_keys,
                trusted_database_path, now):
    """Fail closed before signing-gate consumption unless content is verified.

    All trust anchors, replay-store path and clock come from trusted parent,
    never untrusted message. The only allowed effect remains synthetic_review.
    """
    reply = {"decision": HOLD, "simulated_effect": None}
    try:
        raw = connection.recv_bytes(MAX_MESSAGE)
        request, approval, raw_payload, encodings = _decode(raw)
        decision = guarded_synthetic_review(
            request, approval, raw_payload=raw_payload, encodings=encodings,
            policy=policy, trusted_operator_keys=trusted_operator_keys,
            trusted_database_path=trusted_database_path, now=now)
        if decision == SIMULATED:
            reply = {"decision": SIMULATED, "simulated_effect": "synthetic_review_recorded"}
    except (OSError, EOFError, UnicodeError, ValueError, TypeError, KeyError,
            AttributeError, json.JSONDecodeError):
        pass
    finally:
        try:
            connection.send_bytes(json.dumps(reply, separators=(",", ":")).encode("utf-8"))
        except (BrokenPipeError, OSError, EOFError):
            pass
        connection.close()
