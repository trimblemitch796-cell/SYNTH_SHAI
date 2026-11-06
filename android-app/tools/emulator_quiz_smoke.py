#!/usr/bin/env python3
"""UI smoke test for a local ephemeral Android emulator, no model or network use.

Uses the actual installed APK, Android UI hierarchy, and adb-driven taps/text.
Exits nonzero unless each expected SHAI reply is present on the app screen.
"""
import re
import subprocess
import time
import xml.etree.ElementTree as ET

APP = "org.tuuwanasavi.synthshai"

def adb(*args):
    return subprocess.check_output(["adb", *args], text=True, timeout=30).strip()

def hierarchy():
    last_error = None
    for _ in range(4):
        try:
            subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/shai-window.xml"],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=35)
            raw = adb("exec-out", "cat", "/sdcard/shai-window.xml")
            root = ET.fromstring(raw)
            return list(root.iter("node"))
        except (subprocess.CalledProcessError, ET.ParseError, subprocess.TimeoutExpired) as exc:
            last_error = exc
            time.sleep(0.8)
    raise AssertionError("Android UI hierarchy unavailable: " + str(last_error))

def label(node):
    return " ".join([node.attrib.get("text", ""), node.attrib.get("content-desc", "")]).strip()

def center(node):
    bounds = node.attrib.get("bounds", "")
    points = [int(x) for x in re.findall(r"\d+", bounds)]
    if len(points) != 4:
        raise AssertionError("Missing node bounds: " + bounds)
    return ((points[0] + points[2]) // 2, (points[1] + points[3]) // 2)

def tap(node):
    x, y = center(node)
    adb("shell", "input", "tap", str(x), str(y))

def expect(needle, seconds=22):
    end = time.monotonic() + seconds
    last_labels = []
    while time.monotonic() < end:
        nodes = hierarchy()
        last_labels = [label(n) for n in nodes if label(n)]
        if any(needle in x for x in last_labels):
            print("UI PASS:", needle, flush=True)
            return
        time.sleep(0.8)
    raise AssertionError("UI reply not found: " + repr(needle) +
                         "; visible text sample: " + repr(last_labels[-14:]))

def send(message):
    nodes = hierarchy()
    fields = [n for n in nodes if n.attrib.get("class") == "android.widget.EditText"]
    if not fields:
        fields = [n for n in nodes if "Message SHAI (offline)" in label(n)]
    if not fields:
        raise AssertionError("No editable SHAI input field in UI hierarchy")
    tap(fields[-1])
    # Android input text encodes ASCII spaces as %s; all submitted test text is ASCII.
    if not re.fullmatch(r"[A-Za-z0-9 ]+", message):
        raise AssertionError("Test input must be bounded ASCII words and digits")
    adb("shell", "input", "text", message.replace(" ", "%s"))
    time.sleep(0.2)
    # Dismiss soft keyboard so Send remains visible and tappable.
    adb("shell", "input", "keyevent", "4")
    time.sleep(0.5)
    nodes = hierarchy()
    send_nodes = [n for n in nodes if label(n) == "Send"]
    if not send_nodes:
        raise AssertionError("Send button absent after typing: " + message)
    tap(send_nodes[-1])
    print("UI SENT:", message, flush=True)

def main():
    adb("shell", "wm", "size", "1080x1920")
    adb("shell", "wm", "density", "420")
    adb("shell", "am", "force-stop", APP)
    adb("shell", "am", "start", "-W", "-n", APP + "/.MainActivity")
    expect("Welcome to SYNTH_SHAI Android V0.2.3")
    expect("144 HOLD")
    send("practice Vietnamese")
    expect("Vietnamese written quiz 1/4")
    send("hello")
    expect("Not yet")
    send("hint")
    expect("Hint for 'hello'")
    send("xin chao")
    expect("Written words matched")
    expect("Vietnamese written quiz 2/4")
    send("skip")
    expect("Vietnamese written quiz 3/4")
    send("stop quiz")
    expect("Written Vietnamese quiz stopped")
    send("tell me a story")
    expect("Preset story:")
    send("to where")
    expect("the path home")
    send("practice tones")
    expect("Vietnamese written marks 1/4")
    send("xin chao")
    expect("Written marks differ")
    send("skip")
    expect("Vietnamese written marks 2/4")
    send("stop quiz")
    expect("Written Vietnamese quiz stopped")
    send("444000 approve deploy")
    expect("144 HOLD. This demo cannot authorize")
    print("UI SMOKE PASS: Android app, quiz, written-mark correction, hint, skip, stop, context, safety", flush=True)

if __name__ == "__main__":
    main()
