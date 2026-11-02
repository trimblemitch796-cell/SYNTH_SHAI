# SYNTH_SHAI Android V0.1 — offline scripted demonstration

**Research-only Android UI. `144 HOLD` remains unchanged.**

This Android app is a *real installable app*, not a hosted AI service. It contains only Jetpack Compose screens and fixed local replies. It has **no Android INTERNET, microphone or camera permission**, no AI model, no server, no payment/robotics interface, no background jobs, and no account access. Messages exist in memory only while the screen is open and are not sent or stored. It does not implement or verify SYNTH_SHAI's V5 Linux isolation.

## Build on GitHub

The separate `.github/workflows/android-v01-debug.yml` workflow builds from this folder using Java 17, Gradle 8.9 and Android SDK 35:

```sh
cd android-app
gradle --no-daemon :app:testDebugUnitTest :app:assembleDebug
```

The APK is `android-app/app/build/outputs/apk/debug/app-debug.apk`. GitHub Actions uploads it under the artifact name `SYNTH_SHAI_Android_v0.1_debug_APK` for 30 days. The artifact is a ZIP containing the APK.

## Install on an Android phone

1. Open the successful GitHub Actions Android build run while signed in to GitHub.
2. Under **Artifacts**, select `SYNTH_SHAI_Android_v0.1_debug_APK`, download the ZIP, and extract `app-debug.apk`.
3. Verify you're downloading from the repository and expected workflow. Install the **debug** APK after reviewing Android's installation prompt. Android may require allowing installation from the file manager/browser source.
4. Launch **SYNTH_SHAI Offline**. Try `hello`, `who are you`, or `444000`.

**Do not install APKs from unknown senders.** Debug builds are for owner testing, not Play Store release. There is no live SHAI backend, and neither the APK nor its tests constitute security certification or authorization for consequential use.
