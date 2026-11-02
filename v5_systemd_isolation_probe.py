"""Research-only systemd-run filesystem/network isolation *experiment*.

This is NOT SYNTH_SHAI's worker controller, an authorization endpoint, or a
validated sandbox. Only the known disposable synthetic probe is launched.
Systemd manager must install restrictions before starting the probe.
No deployment or live-use authority is ever granted.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile

HOLD = "144 HOLD"
OBSERVED = "SYNTHETIC_DENIAL_OBSERVED_NOT_AUTHORIZATION"
MAX_OUTPUT = 1024

# Fixed settings, never request-controlled.
REQUIRED_PROPERTIES = (
    "Type=exec",
    "NoNewPrivileges=yes",
    "ProtectSystem=strict",
    "ProtectHome=yes",
    "PrivateNetwork=yes",
    "RestrictAddressFamilies=AF_UNIX",
    "SystemCallFilter=~@mount",
    "CapabilityBoundingSet=",
    "AmbientCapabilities=",
    "KillMode=control-group",
    "SendSIGKILL=yes",
    "RuntimeMaxSec=5s",
    "TimeoutStartSec=5s",
    "TasksMax=16",
    "MemoryMax=256M",
)


@dataclass(frozen=True)
class Observation:
    decision: str
    reason: str
    unit_name: str | None = None


def _pairs_unique(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON field")
        result[name] = value
    return result


def _parse_observation(raw, expected_nonce):
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_OUTPUT:
        return Observation(HOLD, "oversized_or_invalid_output")
    try:
        data = json.loads(raw, object_pairs_hook=_pairs_unique)
    except (TypeError, ValueError):
        return Observation(HOLD, "malformed_response")
    expected = {"kind", "nonce", "file_read_denied", "file_write_denied",
                "inet_socket_denied"}
    if type(data) is not dict or set(data) != expected:
        return Observation(HOLD, "unexpected_reply_fields")
    if data["kind"] != "synthetic_kernel_probe" or data["nonce"] != expected_nonce:
        return Observation(HOLD, "wrong_probe_or_nonce")
    for key in ("file_read_denied", "file_write_denied", "inet_socket_denied"):
        if type(data[key]) is not bool or not data[key]:
            return Observation(HOLD, "restriction_not_observed_" + key)
    return Observation(OBSERVED, "all_three_synthetic_denials_observed")


def _fixed_argv(systemd_binary, protected_directory, nonce, unit_name):
    """No callback, shell, destination or worker name comes from a request."""
    if not protected_directory.is_absolute() or not protected_directory.is_dir():
        raise ValueError("invalid disposable fixture path")
    if not unit_name.startswith("shai-v5-offline-probe-"):
        raise ValueError("not a test unit")
    return [systemd_binary, "--user", "--quiet", "--wait", "--pipe",
            "--collect", "--service-type=exec", f"--unit={unit_name}",
            *(f"--property={prop}" for prop in REQUIRED_PROPERTIES),
            f"--property=InaccessiblePaths={protected_directory}",
            "--", sys.executable, str(Path(__file__).resolve()),
            "--fixture-child", str(protected_directory), nonce]


def run_offline_probe():
    """Request one restricted *test* unit; fail closed on errors/uncertainty.

    No SYNTH_SHAI approval is accepted or consumed. A success never permits work.
    No process-tree cleanup guarantee is made on manager/client crash.
    """
    if not sys.platform.startswith("linux"):
        return Observation(HOLD, "linux_required")
    systemd_binary = shutil.which("systemd-run")
    if systemd_binary is None:
        return Observation(HOLD, "systemd_run_missing")
    with tempfile.TemporaryDirectory(prefix="shai-v5-fake-host-") as temp:
        protected = Path(temp).resolve()
        (protected / "fake-host-secret.txt").write_text(
            "disposable-synthetic-string", encoding="utf-8")
        nonce = secrets.token_hex(16)
        unit_name = "shai-v5-offline-probe-" + secrets.token_hex(8)
        argv = _fixed_argv(systemd_binary, protected, nonce, unit_name)
        try:
            result = subprocess.run(argv, capture_output=True, text=True,
                                    timeout=12, check=False,
                                    stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            # The systemd client's timeout is NOT proof of unit cleanup.
            return Observation(
                HOLD, "manager_or_probe_timeout_cleanup_unverified", unit_name)
        except (OSError, ValueError, UnicodeError):
            return Observation(HOLD, "launcher_failed", unit_name)
        if result.returncode != 0:
            return Observation(HOLD, "systemd_service_failed", unit_name)
        parsed = _parse_observation(result.stdout, nonce)
        return Observation(parsed.decision, parsed.reason, unit_name)


def _fixture_child(directory, nonce):
    """Fixed test target. No bind(), connect(), or network traffic."""
    if not os.path.isabs(directory) or len(nonce) != 32:
        return 2
    file_path = Path(directory, "fake-host-secret.txt")
    target = Path(directory, "fake-host-write.txt")
    denied = {"file_read_denied": False, "file_write_denied": False,
              "inet_socket_denied": False}
    try:
        file_path.read_bytes()
    except (PermissionError, FileNotFoundError):
        denied["file_read_denied"] = True
    try:
        target.write_text("fake-no-secret", encoding="utf-8")
    except (PermissionError, FileNotFoundError):
        denied["file_write_denied"] = True
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM):
            pass
    except OSError:
        denied["inet_socket_denied"] = True
    reply = {"kind": "synthetic_kernel_probe", "nonce": nonce, **denied}
    print(json.dumps(reply, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--fixture-child":
        raise SystemExit(_fixture_child(sys.argv[2], sys.argv[3]))
    if len(sys.argv) != 1:
        raise SystemExit(2)
    response = run_offline_probe()
    print(json.dumps(response.__dict__, sort_keys=True))
    raise SystemExit(0 if response.decision == OBSERVED else 2)
