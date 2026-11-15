# Native load diagnostics — research only / 144 HOLD

## Purpose and scope

Expose warning/error text emitted by the pinned llama.cpp/ggml logger while loading the verified model and initializing the conversation context. Do not guess that a null context necessarily means insufficient memory.

`chat.cpp` registers `llama_log_set` once, with lifetime-stable diagnostic storage, and rejects overlapping native generation calls so messages cannot be attributed to the wrong request. Capture is active only inside the model/context initialization calls. It is inactive during tokenization, prompt processing and reply generation. The existing MainActivity exception handler displays the resulting message; this display path still needs Android validation.

The helper keeps a 4096-byte tail in memory. Reports explicitly mark truncation and replacement of non-ASCII/control bytes for safe JNI exception text. Reports label the stage; absent engine warnings/errors produce an explicit unknown-cause message. Buffer contents are cleared between stages and requests. This adds no file output, network connection, telemetry or prompt/response logging. Engine messages can include model metadata or descriptor paths, so review a report before sharing it.

The Qwen SHA-256 verification, expected model size, descriptor rewind, `/proc/self/fd/` loading method, CPU-only setting and inference limits are unchanged. No app version bump, merge, deployment or installation is part of this change.

## Evidence obtained

Twelve synthetic host diagnostic-buffer cases passed with GCC C++17, strict warnings, AddressSanitizer and UndefinedBehaviorSanitizer. Cases cover disabled capture, ASCII preservation, stage labeling/message order, null/empty input, byte sanitization, exact capacity, truncation/tail retention, clearing after failure, stage reset, scoped shutdown, exception cleanup and concurrent append stress.

These are tests of the helper, not an Android build, JNI integration test, real llama.cpp execution, device-memory diagnosis or successful Qwen inference. They do not establish the cause of the user's phone failure.

Run from repository root (do not define NDEBUG, because these tests use assert):

```sh
c++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread \
  -fsanitize=address,undefined -fno-omit-frame-pointer -g \
  -Iandroid-app/app/src/main/cpp \
  android-app/native-tests/load_diagnostics_test.cpp \
  -o /tmp/shai-load-diagnostics-test
/tmp/shai-load-diagnostics-test
```

Expected result: `PASS: 12 synthetic host diagnostic-buffer cases`.

## Remaining checks

1. Compile/link the Android ARM64 debug APK against the pinned llama.cpp revision and run Android checks. The existing build workflow is not automatically triggered by a push to this diagnostic branch; no test APK is claimed here.
2. With human approval, reproduce the failure on the Android device and inspect the stage plus emitted diagnostic text. Successful checksums alone do not prove inference.
3. Verify a fresh generated reply in airplane mode, stop behavior, repeated attempts and memory cleanup before calling the offline path verified.

## Limits

Only ERROR/WARN callback messages are collected; other levels and continuation-only messages are not. OS process termination, native aborts, exceptions that do not reach this path, and failures with no emitted diagnostics cannot be guaranteed to produce an on-screen cause. Android system/native crash logs may still be necessary. The logger is global and this implementation assumes this wrapper owns its registration. A future engine integration must reconcile logger ownership and concurrency.

The next step is a test build, not merging or installing. Human approval and 144 HOLD remain in force.
