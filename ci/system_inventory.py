"""Read-only CI inventory. File presence is never equivalent to passing tests."""
import json
import os
from pathlib import Path

COMPONENTS = {
    "SHAI": (("shai/twin.py", "verification_v3_1.py"), ("test_shai_twin.py", "test_verification_v3_1.py"), "Offline simulation and verification"),
    "USHAI": (("ushai_catharsis.py",), ("test_ushai_catharsis.py",), "Offline ethical review; no approval authority"),
    "MANIAC": (("maniac/monitor.py", "maniac/simulation.py", "maniac/supervisor.py"), ("test_maniac_monitor.py", "test_maniac_simulation.py", "test_maniac_supervisor.py"), "Synthetic monitor and supervisor"),
    "SHM_RELATED_SENSOR_MONITOR": (("maniac/monitor.py", "maniac/evidence.py"), ("test_maniac_monitor.py", "test_maniac_evidence.py"), "Synthetic sensor/heartbeat tests, NOT dedicated AI SHM"),
    "AAA_DOCTOR": (("synth_shai_doctor/core.py",), ("test_synth_shai_doctor.py",), "Simulation; not clinical software"),
    "ANDROID": (("android-app/app/src/main/java/org/tuuwanasavi/synthshai/OfflineReplies.kt",), ("android-app/app/src/test/java/org/tuuwanasavi/synthshai/OfflineRepliesTest.kt",), "Offline debug APK; manual phone install"),
    "LINUX": (("android-app/linux-cli/src/main/kotlin/org/tuuwanasavi/synthshai/LinuxOfflineChat.kt",), ("android-app/linux-cli/src/test/kotlin/org/tuuwanasavi/synthshai/LinuxOfflineCliTest.kt",), "Offline Linux terminal CLI"),
}
SHM_CANDIDATES = ("shm/__init__.py", "shm.py", "ai_shm/__init__.py", "ai_shm.py", "signal_health_model/__init__.py", "structural_health_monitoring/__init__.py")


def inventory(root: Path) -> dict:
    root = Path(root)
    components = {}
    for name, (sources, tests, scope) in COMPONENTS.items():
        missing_sources = [p for p in sources if not (root / p).is_file()]
        missing_tests = [p for p in tests if not (root / p).is_file()]
        components[name] = {
            "status": "TESTS_CONFIGURED" if not missing_sources and not missing_tests else "INCOMPLETE",
            "missing_sources": missing_sources, "missing_tests": missing_tests, "scope": scope,
        }
    named = [p for p in SHM_CANDIDATES if (root / p).is_file()]
    components["DEDICATED_AI_SHM"] = {
        "status": "SOURCE_CANDIDATE_REQUIRES_REVIEW" if named else "NOT_FOUND_IN_NAMED_PATHS",
        "source_candidates": named,
        "scope": "No claim of operational AI SHM or live sensors",
    }
    return {
        "sha": os.environ.get("GITHUB_SHA") or "local-check",
        "evidence": "SOURCE_INVENTORY_ONLY",
        "authorization": "144 HOLD",
        "components": components,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="build/system-inventory.json")
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = inventory(Path.cwd())
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, info in data["components"].items():
        print(f"{name}: {info['status']}; {info['scope']}")
    print("SOURCE_INVENTORY_ONLY; 144 HOLD; output:", out)


if __name__ == "__main__":
    main()
