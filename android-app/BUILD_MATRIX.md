# SYNTH_SHAI — repeatable GitHub Linux + Android builds

The goal of this bounded setup is to build two **different** offline research artifacts from the **same GitHub commit** on GitHub-hosted Ubuntu Linux runners.

| Build | Runs where | Output |
| --- | --- | --- |
| Linux offline CLI | Ubuntu Linux, Java 17 | `SYNTH_SHAI_Linux_Offline_CLI.zip`, includes the executable shell launch script |
| Android phone APK | Ubuntu Linux, Android SDK 35 | `SYNTH_SHAI_Android_Offline_Debug.apk`, a debug APK for **manual installation** on an Android phone |
| Android interface verification | Ubuntu Linux running an Android emulator | Existing `android-v022-emulator-smoke.yml` separately checks typed UI conversations |

## GitHub Actions workflow

`.github/workflows/shai-linux-android-build.yml` runs two jobs on PRs that change `android-app/**` (or the workflow itself), on matching pushes to `main` and `review/**`, and on manual workflow dispatch. It does not automatically compile unrelated research Python modules into Android APKs. Existing separate repository security and verification jobs remain independent.

Use the Actions run for the **specific commit SHA** you intend to test. Download the artifacts **from that run**. Each includes a `SHA256SUMS.txt` alongside the build; verify it before installing or running.

## Running the Linux build

Extract `SYNTH_SHAI_Linux_Offline_CLI.zip` on Linux and, with Java 17 or newer installed, run:

```sh
./linux-cli/bin/synth-shai-offline
```

The Linux build is a text-only **terminal application**, not the Android Compose UI or a Linux desktop app. It reuses the exact `OfflineReplies.kt` scripted reply engine compiled into Android. Try `practice Vietnamese`, `practice tones`, and `444000 approve deploy`; type `/exit` to quit.

## Installing on Android

Extract the GitHub artifact download ZIP, then open `SYNTH_SHAI_Android_Offline_Debug.apk` on your phone and use Android's installer. GitHub runners **cannot install the app on your personal Android phone remotely**. GitHub Actions validates the APK compile and tests; separate physical-phone testing is still necessary.

Debug builds signed on different CI runners may have incompatible signing keys. In that case Android can refuse the update. Do **not** uninstall an existing working app casually: first verify the source and understand that the offline app's prior in-memory session data will not carry across. The separate SHAI Encouragement app is not part of this build.

## What the tests do not prove

- Passing Linux builds is not independent security verification, end-to-end physical-device installation evidence, or OS-level isolation.
- Both outputs run fixed local scripts. There is no AI model, backend, account access, autonomous task execution or audio pronunciation scoring.
- The scripted `144 HOLD` response is visible demonstration only, not a production authorization mechanism. Consequential real-world use stays at **144 HOLD**.
- These changes are on a separate review branch; nothing is automatically merged into `main` or deployed.
