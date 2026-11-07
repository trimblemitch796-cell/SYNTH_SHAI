# SHAI Gateway Check 0.3.1 (lab)
This separate installable Android package sends a fixed JSON message to the staging gateway handler through a USB or emulator loopback tunnel. The fixture injects synthetic identity, quota decisions and provider output. All four HTTP responses cross the Android networking stack. No production login, provider request or live trial activation is available. 144 HOLD.

## Run on a test phone
Use a trusted test computer with Python, the repository requirements and Android platform tools. Select the intended phone in adb and enable USB debugging for that computer. Install the gateway-check APK. From the repository root run:

    python -m SYNTH_SHAI_staging_gateway.android_loopback_fixture reply

In another terminal run:

    adb reverse tcp:18765 tcp:18765

Open **SHAI Gateway Check** and tap **Run gateway check**. The reply scenario should show HTTP 200. Stop the fixture before selecting another mode: unauthorized (401), limited (429), or closed (503). The APK only sends to 127.0.0.1:18765, bypasses system proxies and refuses redirects. The bearer marker is public fixture data.

Stop the fixture with Ctrl-C and run `adb reverse --remove tcp:18765` when done. Disable USB debugging if you enabled it for this check. The seven-day online trial requires reviewed sign-in and session issuance, a trusted HTTPS gateway, approved quota and shutdown configuration, and explicit activation.
