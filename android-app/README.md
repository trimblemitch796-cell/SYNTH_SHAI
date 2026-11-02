# SYNTH_SHAI Android V0.2 — offline scripted demonstration

**Research-only Android UI. `144 HOLD` remains unchanged.**

This is an installable Kotlin/Jetpack Compose Android demo, **not an AI model or a hosted AI service**. It has no INTERNET, camera or microphone permission; no backend, credentials, payment or robotics interface; no background jobs or account access. Chat text stays in session memory only. The app does not enforce or validate SYNTH_SHAI V5 operating-system isolation.

## V0.2 changes

- Explicit high-contrast light text on the dark background and both message-bubble colours
- Auto-scroll to the newest message using Compose `LazyListState`
- IME-aware input layout with `imePadding` and Android `adjustResize`; a keyboard Send action
- Fixed local topic switching among story, maths, and Vietnamese practice, with a single-session topic label
- A preset short story and a fixed `2 + 2 = 4` example; **not** generative reasoning or a general calculator
- Bounded chat history (maximum 120 visible session messages); no persistence
- New unit tests for topic switching, local follow-ups, preset content and `144 HOLD` priority

Safety-critical input matching is intentionally conservative: any detected action request such as `444000`, `deploy`, or `merge` returns `144 HOLD`. This is visible scripted refusal behaviour only, not a real authorization boundary.

## Build and test on GitHub

The dedicated `.github/workflows/android-v01-debug.yml` workflow builds the `android-app/` Gradle project with Java 17, Gradle 8.9, and Android SDK 35:

```sh
cd android-app
gradle --no-daemon :app:testDebugUnitTest :app:assembleDebug
```

The resulting file is `android-app/app/build/outputs/apk/debug/app-debug.apk`. After successful GitHub Actions verification, download the ZIP artifact `SYNTH_SHAI_Android_v0.2_debug_APK` and extract `app-debug.apk`. Confirm the GitHub workflow ran for the intended commit SHA and check the APK SHA-256 printed by the build before installing.

## Test on an Android phone

1. Download the ZIP artifact from the verified V0.2 GitHub Actions run while signed in to GitHub.
2. Extract `app-debug.apk` and, after reviewing Android's installation prompt, install the debug APK from your own trusted download. Disable install-from-unknown-app permission afterwards if enabled.
3. Launch **SYNTH_SHAI Offline** and check message text contrast and input position with the keyboard open.
4. Send `story`, then `switch to maths`, then `Vietnamese please`, then `tell me more`. These give fixed local responses.
5. Send `444000 approve deploy`. The app should answer `144 HOLD`; it must not attempt any operation.
6. Send several messages in succession and confirm the conversation scrolls to the newest reply.

**Limitations:** local JVM tests and a successful debug APK build do not prove physical-device layout, final merged permissions, full safeguarding or OS isolation. Do not merge or deploy a live backend solely on this evidence; independent security review and explicit human authorization remain separate milestones.
