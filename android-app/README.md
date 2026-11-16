# SYNTH_SHAI Android: experimental offline local chat

**Current source: 0.3.4-screen-state (versionCode 10), reviewed 16 November 2026.**
This describes the source merged in [PR #115](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/115), not a production release or independent safety certification.

The Kotlin/Jetpack Compose app generates text on the device using a separately supplied **Qwen2.5-0.5B-Instruct Q4_K_M GGUF** and the native local engine. It is no longer only the scripted V0.2.3 demonstration. The APK does not contain the model. SHAI is the app/companion identity; the pretrained model supplies the underlying text-generation capability.

## What is implemented, and what is not

- Local text generation with a small recent-conversation prompt, model verification, a private model copy, and Stop/Clear chat controls.
- No INTERNET, camera or microphone permissions in the app manifest; no backend, account integration, or external action executor in this chat path.
- **`144 HOLD` is a displayed project/research-status label, not a generated-output filter.** The current `MainActivity` calls `LocalEngine.generate` directly. The old `OfflineReplies` scripted action matcher is not on this generation path. Do not expect `444000`, `deploy`, or `merge` to reliably produce a HOLD reply.
- The app cannot execute those external actions, but that does not make generated advice safe or accurate. Output can contain errors, invented identity claims, inappropriate content, or repetition. Independent oversight, full safeguarding and SYNTH_SHAI V5 OS isolation are **not established** by this build.
- Conversation context is not model training. The app does not fine-tune the model or establish permanent learning, consciousness or autonomous real-world capabilities.

## Phone setup and model import

The default build targets **ARM64 Android 8.0/API 26 or newer**. The launcher label is **SHAI Load Diagnostics** and the application ID is `org.tuuwanasavi.synthshai.localchat.diagnostics`.

1. Install a trusted APK for the intended commit and compatible device. Downloading a GGUF alone does not install or start an app.
2. In the app, choose **Select GGUF** and select the downloaded model, not an APK or chat export.
3. Wait for **Preparing private model copy…**, then **Model ready**. Send a short message and wait for generation.
4. For an offline check, disable network connectivity, including Wi-Fi if it remains enabled in airplane mode, and repeat a short prompt.

This build accepts the exact model bytes pinned in [LocalEngine.kt](app/src/main/java/org/tuuwanasavi/synthshai/LocalEngine.kt):
- Size: `491400032` bytes.
- SHA-256: `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`.

[VerifiedModelStore.kt](app/src/main/java/org/tuuwanasavi/synthshai/VerifiedModelStore.kt) streams the selected file to app-private no-backup storage, verifies size/hash, and atomically installs the copy. It retains the original download. First import needs approximately **525 MB of additional free storage**; storage space is separate from runtime RAM. The private copy is reverified and reused for subsequent generations. A successful file verification does not guarantee that native inference will succeed on every device.

## Local history, privacy and interruptions

- Recent **completed exchanges and the unsent draft persist locally** in app-private SharedPreferences. Android backup is disabled in the manifest; this is not a claim of encryption or protection against a compromised device.
- Saved history is bounded to at most 40 lines (20 exchanges), 24,000 characters overall and 4,096 characters per line. The visible session can hold up to 120 lines. Each generation includes only the last four conversation lines plus the new message, not the entire saved history.
- **Clear chat** removes saved chat and draft when the button is available; it does not delete the model or its original download.
- The screen stays awake while work is busy and the view is visible. This is not background generation, a wake lock, or protection against the power button, process termination or every rotation/lock interruption. An unfinished response may be lost; previously lost history cannot be reconstructed.
- **Stop** is cooperative, not an immediate interruption of every native loading step. The app records generation attempt time/process ID for exit diagnostics, not a separate chat telemetry log.
- Uninstalling or clearing app data can delete private history and the private model copy. A debug APK signed with a different key cannot update the installed app in place. Do not treat uninstalling as a harmless update workaround.

See [MainActivity.kt](app/src/main/java/org/tuuwanasavi/synthshai/MainActivity.kt), [ChatHistoryCodec.kt](app/src/main/java/org/tuuwanasavi/synthshai/ChatHistoryCodec.kt) and [AndroidManifest.xml](app/src/main/AndroidManifest.xml) for the actual behavior.

## Build and review

The [Android debug workflow](../.github/workflows/android-v01-debug.yml) uses Java 17, Gradle 8.9, Android SDK 35, NDK 27.2.12479018 and CMake 3.22.1:

```sh
cd android-app
gradle --no-daemon :app:testDebugUnitTest :app:assembleDebug
```

The output is `android-app/app/build/outputs/apk/debug/app-debug.apk`. The workflow artifact is named `SYNTH_SHAI_Android_Local_Diagnostics_<commit SHA>` and includes `BUILD_INFO.txt` and `SHA256SUMS.txt`; artifacts expire after seven days. Verify the run's source commit and APK hash. The workflow runs for matching pull requests and selected development branches, **not automatically for every push to main**. Public source availability is not a guarantee of an available, signed, ready-to-install release.

The default ABI is `arm64-v8a`; `-PshaiAbi=x86_64` is available for matching emulator builds, not ordinary ARM64 phone installation. Unit tests include historical scripted behavior and newer storage/history helpers. Passing those tests or building an APK does not certify generated-response safety, factual accuracy, all device lifecycle behavior or independent security review.

## Historical archive: scripted V0.2–V0.2.3

**Archived as history on 16 November 2026, not current installation or behavior guidance.**
The original demonstration notes below describe the earlier fixed-response implementation. Their session-only storage, preset quizzes, action-triggered HOLD replies, old app name and artifact name do **not** describe the current local-model chat. They are retained to explain the project's progression.

---

### SYNTH_SHAI Android V0.2.3 — offline scripted demonstration

**Research-only Android UI. `144 HOLD` remains unchanged.**

This is an installable Kotlin/Jetpack Compose Android demo, **not an AI model or a hosted AI service**. It has no INTERNET, camera or microphone permission; no backend, credentials, payment or robotics interface; no background jobs or account access. Chat text stays in session memory only. The app does not enforce or validate SYNTH_SHAI V5 operating-system isolation.

#### V0.2 changes

- Explicit high-contrast light text on the dark background and both message-bubble colours
- Auto-scroll to the newest message using Compose `LazyListState`
- IME-aware input layout with `imePadding` and Android `adjustResize`; a keyboard Send action
- Fixed local topic switching among story, maths, and Vietnamese practice, with a single-session topic label
- A preset short story and a fixed `2 + 2 = 4` example; **not** generative reasoning or a general calculator
- Bounded chat history (maximum 120 visible session messages); no persistence
- New unit tests for topic switching, local follow-ups, preset content and `144 HOLD` priority

Safety-critical input matching is intentionally conservative: any detected action request such as `444000`, `deploy`, or `merge` returns `144 HOLD`. This is visible scripted refusal behaviour only, not a real authorization boundary.

#### Build and test on GitHub

The dedicated `.github/workflows/android-v01-debug.yml` workflow builds the `android-app/` Gradle project with Java 17, Gradle 8.9, and Android SDK 35:

```sh
cd android-app
gradle --no-daemon :app:testDebugUnitTest :app:assembleDebug
```

The resulting file is `android-app/app/build/outputs/apk/debug/app-debug.apk`. After successful GitHub Actions verification, download the ZIP artifact `SYNTH_SHAI_Android_v0.2.3_debug_APK` and extract `app-debug.apk`. Confirm the GitHub workflow ran for the intended commit SHA and check the APK SHA-256 printed by the build before installing.

#### Test on an Android phone

1. Download the ZIP artifact from the verified V0.2 GitHub Actions run while signed in to GitHub.
2. Extract `app-debug.apk` and, after reviewing Android's installation prompt, install the debug APK from your own trusted download. Disable install-from-unknown-app permission afterwards if enabled.
3. Launch **SYNTH_SHAI Offline** and check message text contrast and input position with the keyboard open.
4. Send `story`, then `switch to maths`, then `Vietnamese please`, then `tell me more`. These give fixed local responses.
5. Send `444000 approve deploy`. The app should answer `144 HOLD`; it must not attempt any operation.
6. Send several messages in succession and confirm the conversation scrolls to the newest reply.

**Limitations:** local JVM tests and a successful debug APK build do not prove physical-device layout, final merged permissions, full safeguarding or OS isolation. Do not merge or deploy a live backend solely on this evidence; independent security review and explicit human authorization remain separate milestones.

#### V0.2.1 bounded conversation corrections

- Keep only last preset reply context in session memory: a story-told flag and a four-phrase Vietnamese lesson counter. Unrelated inputs reset topic context; nothing is stored or inferred beyond these explicit labels.
- Accept Vietnamese tone-mark variants such as `Xin chào` / `Xin chao` and `tiếng Việt` / `tieng viet`; neither case constitutes general Vietnamese understanding.
- After the lantern story, `to where` refers only to the documented path home. Repeated `tell me more` steps through four fixed Vietnamese phrases rather than looping the first phrase.
- Recognise `math 2-2=` as an additional *fixed* example. No general arithmetic execution, model, network or tool actions are introduced.
- Respond to `ready` by identifying this chat as separate from the independently installed encouragement app; notification scheduling is outside this branch's scope.
- Added local JVM regression tests. These tests do not establish end-to-end physical-device behaviour, independent validation, OS isolation or permission for consequential actions. **144 HOLD remains.**


#### V0.2.2: Vietnamese written tutor (offline, fixed content)

- Type \`practice Vietnamese\` or \`quiz me\` to start a **four-question written practice** on *Xin chào*, *Cảm ơn*, *Tôi không hiểu*, and *Bạn có thể nói chậm hơn không?*
- One English-to-Vietnamese question appears at a time. Exact preset Vietnamese words are checked after case and diacritic normalization. SHAI shows standard spelling, but **cannot verify tones, pronunciation, grammar outside the presets, speech, or arbitrary translations**.
- Wrong answers stay on the same question and give a bounded hint; a second mistake shows the reference phrase. \`hint\`, \`repeat\`, \`skip\`, \`stop quiz\` are supported. Explicit story/math topic switches exit the quiz.
- Safety overrides are checked **before** all quiz answers; \`444000 approve deploy\` and \`144 HOLD\` always return the safety hold. No network access, background learning, external tool access, score persistence, recordings or model inference are added.
- Regression tests cover four-step progress, accented/unaccented responses, wrong-answer corrections, hints, skips, stop, topic changes, and safety priority.

Physical-device testing is still required after CI. A successful unit test and debug APK are not independent validation. **144 HOLD remains.**

#### V0.2.3: opt-in written Vietnamese marks check

- Enter `practice tones` (or `tone quiz`) for a separate four-question **written-mark accuracy** exercise using the same preset phrases.
- Unlike the normal `practice Vietnamese` quiz, this mode requires Unicode-normalized spelling with the expected Vietnamese accents, vowel marks and letters. For example, `xin chao` triggers **"Written marks differ"**, displays the standard `Xin chào`, and stays on the same question; `Xin chào` advances.
- The existing accent-tolerant vocabulary quiz is unchanged. Both modes use only four fixed examples. This is comparison of **typed characters**, not pronunciation, acoustic tone recognition, or broad language understanding.
- The mode preserves hints, repeat, skip, stop, restart and explicit topic changes. `144 HOLD` and action blocking still run before lesson processing. No network, microphone, external tools, persistent data or new permissions.
- Added Kotlin regression tests and a Linux-hosted Android UI smoke sequence for missing written marks, skipped questions and the hold response. Physical-device observation remains separate from CI. **144 HOLD remains.**
