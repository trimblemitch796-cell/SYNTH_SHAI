# Native model loading and diagnostics — research only / 144 HOLD

## Current path (0.3.4-screen-state)

The app imports the single supported Qwen2.5-0.5B-Instruct Q4_K_M GGUF through Android's file picker. `VerifiedModelStore` streams into an app-private temporary file using a 64 KiB buffer, checks the exact 491,400,032-byte size and SHA-256 `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`, syncs the file, then atomically promotes it. Incorrect, interrupted or cancelled imports are not promoted; temporary imports are cleaned. The original download is not modified. A verified private copy is reused and rehashed before loading. First import requires approximately 525 MB free storage, including a reserve.

The native engine now opens the real app-private pathname. It no longer uses `/proc/self/fd` for inference: that reopen returned permission-denied on the user's device even though reading the Android-granted descriptor worked. The descriptor preflight remains as a regression-test helper. No storage-permission or security-policy bypass is used.

`chat.cpp` registers the llama logger once and serializes native generation. Initialization warnings/errors enter a bounded 4,096-byte tail buffer. The pinned upstream GGUF reader originally wrote detailed errors directly to stderr; CMake routes those specific `gguf.cpp` error calls to the logger. Known private model paths are redacted before buffering. Capture is disabled during prompt processing/reply generation. No network, prompt or response telemetry is added.

Native exceptions are caught at the JNI boundary; Java allocation errors receive a bounded user-facing message. These catches cannot recover from native signals, aborts or Android process killing. On Android 11+, a persisted attempt timestamp/PID can correlate a subsequent interrupted attempt with Android's reported process-exit reason. No conversation is stored in exit diagnostics.

## UI/lifecycle and local data

While work is active, the visible view requests that the screen remain on. Explicit locking, backgrounding and process termination are still respected; there is no wake-lock permission, foreground service or background-generation guarantee. Recent completed exchanges (up to 20 pairs, 24,000 characters) and the draft are saved in app-private preferences. Clear chat removes both saved history and draft. Android backup is disabled. This cannot recover conversations lost before the persistence update.

## Evidence and limitations

- Android debug build and 65 JVM tests passed locally for the 0.3.4 artifact. These comprise 48 older scripted/auth tests and 17 private-copy/history/exit-message tests, not 65 generative-model safety tests.
- Twelve native diagnostic-buffer cases and descriptor/path preflight regression assertions passed with AddressSanitizer/UndefinedBehaviorSanitizer. LeakSanitizer was disabled in the restricted container because ptrace prevents it running; no leak-check claim is made.
- A host harness with the exact pinned llama revision and hash-verified model passed first/follow-up prompts and 128-token batch boundaries (36, 153, 162, 292, 732 tokens). A 982-token prompt was rejected safely. This is not ARM/Android lifecycle or low-memory verification.
- The user reported Android airplane-mode replies. This has not been independently observed as a device test.

## Release/review holds

The package remains `org.tuuwanasavi.synthshai.localchat.diagnostics`, labeled `SHAI Load Diagnostics`, signed as a debug research build. Generated responses bypass the old scripted `OfflineReplies` path; there is no connected generated-output safeguard. The 144 HOLD label does not establish response safety, consciousness, independent oversight or authority to take actions. The app exposes no action tools and has no Internet/camera/microphone permission.

Do not present this build as production-ready. Before merge/release approval: review the exact source commit, add/test the intended input/output safeguards, run CI on that commit, resolve stable signing/update provenance, and verify device stop/reopen/screen-off behavior. CI creates fresh debug signing credentials; its APK will not necessarily update an existing locally signed installation. Never commit signing keys, models, APKs or build caches.

## Host helper tests

From repository root:

```sh
for test in load_diagnostics model_file_preflight; do
  c++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -Iandroid-app/app/src/main/cpp \
    android-app/native-tests/${test}_test.cpp -o /tmp/shai-${test}-test
  /tmp/shai-${test}-test
done
```

Use `ASAN_OPTIONS=detect_leaks=0` only where required by the test environment, and disclose that limitation. Android tests/build: `gradle --no-daemon :app:testDebugUnitTest :app:assembleDebug` from `android-app`, using the pinned SDK/NDK/CMake/Gradle versions in the workflow.
