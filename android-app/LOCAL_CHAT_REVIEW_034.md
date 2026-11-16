# Local chat consolidation 0.3.2–0.3.4 — review only

144 HOLD remains in force. This consolidates local work on diagnostic base `88da2ad966123a8f3885bd45bba3093b123ae12d`; it is not approval to merge or distribute a production release.

## Intended changes

1. Preserve the isolated diagnostic app ID/label. Version code 10, version name `0.3.4-screen-state`.
2. Replace descriptor-path model loading with a verified, atomic app-private copy and a real pathname.
3. Improve bounded native diagnostics, redact private paths, and handle native/JVM allocation failures without claiming all process exits can be caught.
4. Record privacy-limited interrupted-generation metadata and display Android's exit reason when available.
5. Keep the visible screen awake only during work; restore bounded recent chat/draft; clear stored state through Clear chat.
6. Add native/JVM helper tests and exclude build artifacts/signing material from source control.

## Main-branch impact

At inspection, main `f3f219769634efc485b87ac1fbd027ef326201f9` used scripted `OfflineReplies.reply`. The full review difference adds the native model/runtime and replaces that scripted path with generated text. This is a larger behavior/safety change than the three bugfix versions alone.

## Blocking review decisions

- No generated-output safeguard is wired into the Qwen path. Old scripted safety tests do not cover it. Define the desired safeguards and test both input and generated output before claiming safety.
- Updated emulator CI exercises the current local-model UI, real offline first/followup inference and chat/draft restoration. Its seeded private-model fixture does not test the Android file-picker import path, ARM64 hardware behavior, or all low-memory/screen-off cases. User phone reports remain distinct from independently recorded checks.
- Local debug signing is not reproducible on a fresh GitHub runner. Choose an approved signing/update process; do not upload keys into the repository.
- The Android workflow triggers on PRs affecting Android paths, and pushes only to its two existing research branches. It does not trigger on main pushes or arbitrary review-branch pushes. Opening a PR can run checks; a source push alone must not be reported as validated. No workflow publication behavior is changed by this consolidation.
- Run repository security/dependency checks on the exact reviewed commit. A local current-tree secret scan cannot establish the safety of every historical Git object or dependency.

See `native-tests/LOAD_DIAGNOSTICS.md` for model provenance, data storage, checks and limitations. No APK, GGUF, signing key, generated build folder or private chat data belongs in this change.

## CI compatibility follow-up

The original exact-head run exposed two real integration failures: Linux CLI accidentally included Android-only helpers through a broad source glob, and the emulator attempted to launch the retired package/activity. The CLI now explicitly shares only its pure scripted engine. Emulator CI builds a matching x86_64 variant and tests the current native app instead of its obsolete quiz UI; phone builds remain ARM64. Existing scripted JVM/CLI safety and tutoring tests are retained. No failing check is disabled or made non-blocking.
