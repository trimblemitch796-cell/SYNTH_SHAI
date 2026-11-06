"""Operator-only Render suspension helper. Default DRY RUN. No scheduler configured."""
import argparse
from datetime import datetime, timezone
import os
import re
import time
from urllib import request

SERVICE_RE = re.compile(r"^srv-[a-z0-9]{8,64}$")


def due(deadline_utc, *, now=None):
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
                            deadline_utc):
            return False
        deadline = datetime.strptime(deadline_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
        t = time.time() if now is None else now
        return type(t) in (int, float) and t >= deadline
    except (TypeError, ValueError, OverflowError):
        return False


def suspend_if_due(*, service_id, token, deadline_utc, execute=False,
                   approved=False, opener=request.urlopen, now=None):
    """Network POST is impossible unless due AND flags AND secrets are present."""
    if not due(deadline_utc, now=now):
        return "not_due"
    if not execute or not approved:
        return "dry_run"
    if not SERVICE_RE.fullmatch(service_id or "") or not token or len(token) < 20:
        return "invalid_configuration"
    endpoint = "https://api.render.com/v1/services/" + service_id + "/suspend"
    req = request.Request(endpoint,
                          headers={"Authorization":"Bearer " + token,
                                   "Accept":"application/json"},
                          method="POST")
    try:
        with opener(req, timeout=15) as response:
            return "suspend_accepted" if response.status == 202 else "suspend_not_confirmed"
    except Exception:
        return "suspend_not_confirmed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = suspend_if_due(
        service_id=os.environ.get("SHAI_RENDER_SERVICE_ID"),
        token=os.environ.get("SHAI_RENDER_API_KEY"),
        deadline_utc=os.environ.get("SHAI_PILOT_DEADLINE_UTC", ""),
        execute=args.execute,
        approved=os.environ.get("SHAI_SUNSET_APPROVED") == "YES",
    )
    # Never display tokens or credentials.
    print(result)
    if result == "suspend_not_confirmed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
