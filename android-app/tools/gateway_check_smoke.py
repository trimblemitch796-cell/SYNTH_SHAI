"""Drive the installed Android app through four gateway HTTP outcomes over adb reverse."""
import socket
import subprocess
import sys
import time

from emulator_quiz_smoke import adb, expect, hierarchy, label, tap


def probe(expected):
    # Restart between cases so a stale label cannot satisfy the assertion.
    app = "org.tuuwanasavi.synthshai.gatewaycheck"
    adb("shell", "am", "force-stop", app)
    adb("shell", "am", "start", "-W", "-n", app + "/.GatewayCheck")
    expect("Run gateway check")
    button = next(node for node in hierarchy() if label(node).lower() == "run gateway check")
    tap(button)
    expect(expected)


def main():
    adb("reverse", "tcp:18765", "tcp:18765")
    try:
        for mode, expected in [
            ("reply", "HTTP 200"), ("unauthorized", "HTTP 401"),
            ("limited", "HTTP 429"), ("closed", "HTTP 503")
        ]:
            proc = subprocess.Popen([sys.executable, "-m", "SYNTH_SHAI_staging_gateway.android_loopback_fixture", mode])
            try:
                for _ in range(50):
                    if proc.poll() is not None:
                        raise RuntimeError("Local fixture failed to start")
                    try:
                        with socket.create_connection(("127.0.0.1", 18765), timeout=.2):
                            break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise RuntimeError("Local fixture readiness timed out")
                probe(expected)
            finally:
                proc.terminate()
                proc.wait(timeout=5)
        probe("Local gateway unreachable")
    finally:
        adb("reverse", "--remove", "tcp:18765")


if __name__ == "__main__":
    main()
