#!/usr/bin/env python3
"""Real local-Qwen smoke test on a DISPOSABLE, already-booted Android emulator.

Usage: python3 emulator_local_chat_smoke.py /path/to/verified/qwen.gguf
Requires the installed debuggable x86_64 local-chat APK and adb on PATH.
This clears only this test package, then seeds app-private GGUF and preferences
with run-as. It tests actual inference/UI/persistence, NOT SAF selection, model
import/copy, or phone/ARM compatibility. No behavior mocks or scripted replies.
The fixture URI is deliberately unreadable: inference must use the verified
private model. No chats/replies are seeded. Airplane mode remains enabled.
"""
import argparse
import base64
import hashlib
import re
import struct
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

APP = "org.tuuwanasavi.synthshai.localchat.diagnostics"
ACTIVITY = APP + "/org.tuuwanasavi.synthshai.MainActivity"
SIZE = 491400032
SHA256 = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
PRIVATE_MODEL = "no_backup/verified-model/qwen-verified.gguf"
PREFS = "shared_prefs/local_model.xml"
FIRST = "Mira has a compass and a peach Which item can Mira eat Answer with one word"
SECOND = "Which item could help her find north Answer with one word"
DRAFT = "Unsent draft survives restart"


def adb(*args, timeout=35):
    return subprocess.check_output(["adb", *args], text=True, timeout=timeout).strip()


def private_command(command, *, input_file=None, data=None, timeout=180):
    # One remote command string: quote sh -c so redirection runs under run-as.
    quoted = "'" + command.replace("'", "'\\''") + "'"
    args = ["adb", "exec-in", f"run-as {APP} sh -c {quoted}"]
    if input_file is not None:
        with open(input_file, "rb") as stream:
            subprocess.run(args, stdin=stream, check=True, timeout=timeout)
    else:
        subprocess.run(args, input=data, check=True, timeout=timeout)


def hierarchy():
    error = None
    for _ in range(4):
        try:
            adb("shell", "uiautomator", "dump", "/sdcard/shai-local-window.xml")
            return ET.fromstring(adb("exec-out", "cat", "/sdcard/shai-local-window.xml"))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ET.ParseError) as exc:
            error = exc
            time.sleep(0.5)
    raise AssertionError(f"UI hierarchy unavailable: {error}")


def nodes(root):
    return [n for n in root.iter("node") if n.get("package") == APP]


def label(node):
    return (node.get("text", "") or node.get("content-desc", "")).strip()


def control(root, text):
    parents = {child: parent for parent in root.iter() for child in parent}
    found = [n for n in nodes(root) if label(n) == text]
    if not found:
        raise AssertionError(f"Missing UI control {text!r}")
    original = node = found[-1]
    while True:
        if node.get("class") == "android.widget.Button" or node.get("clickable") == "true":
            return node
        parent = parents.get(node)
        if parent is None or parent.tag != "node" or parent.get("package") != APP:
            return original
        node = parent


def field(root):
    found = [n for n in nodes(root) if n.get("class") == "android.widget.EditText"]
    if len(found) != 1:
        raise AssertionError(f"Expected one message field, found {len(found)}")
    return found[0]


def tap(node):
    points = [int(x) for x in re.findall(r"-?\d+", node.get("bounds", ""))]
    assert len(points) == 4, "Control has no bounds"
    adb("shell", "input", "tap", str((points[0] + points[2]) // 2), str((points[1] + points[3]) // 2))


def wait_ui(predicate, description, seconds=40):
    end = time.monotonic() + seconds
    last = []
    while time.monotonic() < end:
        root = hierarchy()
        last = [label(n) for n in nodes(root) if label(n)]
        if predicate(root):
            print("UI PASS:", description, flush=True)
            return root
        time.sleep(0.5)
    raise AssertionError(f"Timed out: {description}; visible={last[-12:]!r}")


def has_text(root, text):
    return any(label(n) == text for n in nodes(root))


def launch():
    result = adb("shell", "am", "start", "-W", "-n", ACTIVITY)
    assert "Error" not in result, result
    return wait_ui(lambda r: has_text(r, "SYNTH_SHAI"), "activity opened")


def type_draft(message):
    """Paced UI injection; never send text that the app has not saved exactly.

    Some emulator/IME combinations lose fast adb input. Accessibility may also
    expose only a clipped segment of a multiline editor. The app's own saved
    chat_draft is authoritative, and generate() later verifies the saved user turn.
    No preference is written here: every character still enters through the UI.
    """
    assert re.fullmatch(r"[A-Za-z0-9 ]+", message), "Fixture must be ASCII words/digits"
    assert len(message) <= 1000, "Fixture exceeds the actual draft limit"

    def wait_saved(expected, seconds=4):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            actual = read_prefs().get("chat_draft") or ""
            if actual == expected:
                return True
            time.sleep(0.15)
        return False

    def clear_for_retry():
        current = field(hierarchy())
        assert current.get("enabled") == "true", "Message field disabled during retry"
        tap(current)
        adb("shell", "input", "keyevent", "KEYCODE_MOVE_END")
        saved = read_prefs().get("chat_draft") or ""
        # Extra deletes cover any late input from the failed attempt. Bounded,
        # paced groups avoid the same burst-input problem during clearing.
        count = max(len(saved), len(current.get("text", "")), len(message)) + 8
        for offset in range(0, count, 8):
            adb("shell", "input", "keyevent", *(["KEYCODE_DEL"] * min(8, count - offset)))
            time.sleep(0.15)
        assert wait_saved(""), "Could not clear incorrect draft; refusing to Send"
        assert not field(hierarchy()).get("text", ""), "Editor still contains text after clearing"

    current = field(hierarchy())
    assert current.get("enabled") == "true", "Message field disabled"
    assert not current.get("text", ""), "Expected empty draft before typing"
    assert not (read_prefs().get("chat_draft") or ""), "Expected empty saved draft before typing"
    last_actual = ""
    for attempt in range(3):  # Initial attempt plus at most two retries.
        if attempt:
            print(f"INPUT RETRY {attempt}/2: app did not save the exact prefix; never sent", flush=True)
            clear_for_retry()
        tap(field(hierarchy()))
        complete = True
        for offset in range(0, len(message), 8):
            chunk = message[offset:offset + 8]
            adb("shell", "input", "text", chunk.replace(" ", "%s"))
            time.sleep(0.15)
            if not wait_saved(message[:offset + len(chunk)]):
                last_actual = read_prefs().get("chat_draft") or ""
                complete = False
                break
        if not complete:
            continue
        assert wait_saved(message), "Full saved draft changed after prefix verification"
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        visible = field(hierarchy()).get("text", "")
        actual = read_prefs().get("chat_draft") or ""
        if actual == message and visible and visible in message:
            if visible != message:
                print("INPUT NOTE: accessibility shows a clipped segment; full saved draft verified", flush=True)
            print("UI PASS: exact full draft saved through paced input", flush=True)
            return
        last_actual = actual
    raise AssertionError("Emulator input failed after two retries; refusing to Send. "
                         f"Expected={message!r}, saved={last_actual!r}")


def read_prefs():
    # SharedPreferences may be atomically replacing its XML while we inspect it.
    error = None
    for _ in range(4):
        try:
            raw = adb("exec-out", "run-as", APP, "cat", PREFS)
            root = ET.fromstring(raw)
            return {n.get("name"): (n.text if n.tag == "string" else n.get("value")) for n in root}
        except (subprocess.CalledProcessError, ET.ParseError) as exc:
            error = exc
            time.sleep(0.2)
    raise AssertionError(f"Saved app preferences unavailable: {error}")


def history():
    encoded = read_prefs().get("chat_history")
    if not encoded:
        return []
    raw = base64.b64decode(encoded, validate=True)
    assert len(raw) >= 8, "Truncated saved history"
    version, count = struct.unpack_from(">ii", raw)
    assert version == 1 and count % 2 == 0 and 0 <= count <= 40, "Invalid history header"
    offset, result = 8, []
    for index in range(count):
        assert offset + 3 <= len(raw), "Truncated saved record"
        human, length = struct.unpack_from(">BH", raw, offset)
        offset += 3
        assert human == (1 if index % 2 == 0 else 0), "Incorrect saved roles"
        assert offset + length <= len(raw), "Truncated saved message"
        # DataOutputStream.writeUTF uses modified UTF-8, including surrogate pairs.
        value = raw[offset:offset + length].replace(b"\xc0\x80", b"\0").decode("utf-8", "surrogatepass")
        value = value.encode("utf-16le", "surrogatepass").decode("utf-16le")
        result.append((bool(human), value))
        offset += length
    assert offset == len(raw), "Unexpected trailing history bytes"
    return result


def window_holds_screen():
    dump = adb("shell", "dumpsys", "window", "windows")
    # API-dependent diagnostic only: do not mistake an unrelated window's flag.
    if re.search(r"mHoldScreenWindow=Window\{[^}\n]*" + re.escape(APP), dump):
        return True
    for block in re.split(r"\n\s*Window #\d+", dump):
        if APP not in "\n".join(block.splitlines()[:2]):
            continue
        if "KEEP_SCREEN_ON" in block:
            return True
        for flags in re.findall(r"\bfl=(?:0x)?([0-9a-fA-F]+)\b", block):
            if int(flags, 16) & 0x80:
                return True
    return False


def generate(message, expected_pairs, expected_answer, timeout):
    type_draft(message)
    send = control(hierarchy(), "Send")
    assert send.get("enabled") == "true", "Send unexpectedly disabled"
    tap(send)
    deadline = time.monotonic() + timeout
    observed_busy = observed_awake = False
    while time.monotonic() < deadline:
        root = hierarchy()
        if has_text(root, "Generating on this phone…") or has_text(root, "Stop"):
            observed_busy = True
            observed_awake |= window_holds_screen()
        saved = history()
        if len(saved) == expected_pairs * 2 and has_text(root, "Model ready"):
            assert saved[-2] == (True, message), "Saved user turn differs from submitted input"
            answer = saved[-1][1]
            assert saved[-1][0] is False and answer.strip(), "No actual assistant-role output"
            assert answer not in (FIRST, SECOND), "Prompt echoed instead of an answer"
            assert re.fullmatch(r"\s*" + re.escape(expected_answer) + r"[.!]?\s*", answer, re.IGNORECASE), f"Unexpected generated answer: {answer!r}"
            assert has_text(root, answer.strip()), "Generated assistant output not displayed in UI"
            assert not field(root).get("text", ""), "Successful send did not clear draft"
            print(f"INFERENCE PASS: turn {expected_pairs}, assistant={answer!r}", flush=True)
            print(f"SCREEN-AWAKE observation: busy={observed_busy}, hold_flag={observed_awake}; "
                  "informational, not a screen/power-button guarantee", flush=True)
            return saved
        assert adb("shell", "pidof", APP), "App process exited during generation"
        time.sleep(0.5)
    raise AssertionError(f"Inference turn {expected_pairs} failed/timed out; visible=" +
                         repr([label(n) for n in nodes(hierarchy()) if label(n)]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--generation-timeout", type=int, default=300)
    args = parser.parse_args()
    assert adb("shell", "getprop", "ro.kernel.qemu") == "1", "Refusing to clear data on a non-emulator device"
    assert args.model.stat().st_size == SIZE, "Wrong model fixture size"
    digest = hashlib.sha256()
    with args.model.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    assert digest.hexdigest() == SHA256, "Wrong model fixture hash"
    adb("shell", "run-as", APP, "id")  # Must be debuggable; no root/security bypass.
    adb("shell", "wm", "size", "1080x1920")
    adb("shell", "wm", "density", "420")
    assert adb("shell", "pm", "clear", APP) == "Success", "Failed to reset disposable test app"
    root = launch()
    assert has_text(root, "Select the Qwen2.5-0.5B-Instruct Q4_K_M file"), "No-model state absent"
    assert control(root, "Send").get("enabled") == "false", "Send enabled without a model"
    assert field(root).get("enabled") == "false", "Input enabled without a model"
    assert control(root, "Select GGUF").get("enabled") == "true", "Model picker unavailable"
    print("UI PASS: real no-model screen and disabled Send/input", flush=True)
    adb("shell", "am", "force-stop", APP)
    private_command(f"mkdir -p no_backup/verified-model shared_prefs; cat > {PRIVATE_MODEL}", input_file=args.model)
    actual = adb("shell", "run-as", APP, "sha256sum", PRIVATE_MODEL).split()[0]
    assert actual == SHA256, "On-emulator model fixture hash mismatch"
    fixture = b'<?xml version="1.0" encoding="utf-8"?><map><string name="uri">content://shai.test.fixture/unreadable</string></map>'
    private_command(f"cat > {PREFS}", data=fixture)
    print("FIXTURE: private model + URI seeded; no chats/replies seeded; NOT a SAF/import test", flush=True)
    adb("shell", "cmd", "connectivity", "airplane-mode", "enable")
    adb("shell", "svc", "wifi", "disable")
    adb("shell", "svc", "data", "disable")
    assert adb("shell", "settings", "get", "global", "airplane_mode_on") == "1", "Airplane mode not enabled"
    launch()
    generate(FIRST, 1, "peach", args.generation_timeout)
    completed = generate(SECOND, 2, "compass", args.generation_timeout)
    type_draft(DRAFT)
    deadline = time.monotonic() + 10
    while read_prefs().get("chat_draft") != DRAFT and time.monotonic() < deadline:
        time.sleep(0.2)
    assert read_prefs().get("chat_draft") == DRAFT, "Draft not saved before restart"
    adb("shell", "am", "force-stop", APP)
    launch()
    root = wait_ui(lambda r: field(r).get("text") == DRAFT and has_text(r, completed[-1][1].strip()),
                   "draft and latest actual answer restored")
    assert history() == completed, "Saved conversation changed during relaunch"
    # LazyColumn may not compose the first turn until scrolled. Saved roles/content
    # and visible final answer jointly establish restoration without a substring match.
    tap(control(root, "Clear chat"))
    root = wait_ui(lambda r: has_text(r, "Chat cleared"), "Clear chat acknowledged")
    assert not field(root).get("text", ""), "Clear chat left a draft"
    assert not history() and not read_prefs().get("chat_draft"), "Clear chat did not clear persistence"
    assert not any(has_text(root, text.strip()) for _, text in completed), "Old chat still visible after clear"
    adb("shell", "am", "force-stop", APP)
    root = launch()
    assert not field(root).get("text", "") and not history(), "Cleared state returned after restart"
    assert not any(has_text(root, text.strip()) for _, text in completed), "Cleared chat restored on screen"
    assert adb("shell", "settings", "get", "global", "airplane_mode_on") == "1"
    print("LOCAL CHAT SMOKE PASS: actual offline inference/followup, saved history/draft, restart and clear", flush=True)


if __name__ == "__main__":
    main()
