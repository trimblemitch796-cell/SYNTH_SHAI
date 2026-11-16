# SYNTH_SHAI: repository and build map

Navigation snapshot: **16 November 2026, after PR #115 merged**. This page separates existing workstreams; it does not merge them or certify a release.

**144 HOLD remains unchanged.** Research results, successful builds and model replies do not authorize consequential actions or establish independent security validation. The HOLD label is not evidence that generated-output safeguards or independent USHAI oversight are implemented or verified.

## Start here

- [Project purpose and terminology](../README.md)
- [Verified core inventory](VERIFIED_CORE.md): evidence and design-only boundaries
- [Threat model](THREAT_MODEL.md): limitations and unresolved security assumptions
- [Build status](BUILD_STATUS.md): milestone history

## Choose the right workstream

| Workstream | Where to look | What it is, and is not |
| --- | --- | --- |
| Current main: experimental Android local chat 0.3.4 | [merged PR #115](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/115) and [local-chat review](https://github.com/trimblemitch796-cell/SYNTH_SHAI/blob/main/android-app/LOCAL_CHAT_REVIEW_034.md) | On-device generated Qwen text, private GGUF import, load/exit diagnostics and bounded chat/draft restoration. Research only, not a certified production or safety release. |
| Historical scripted Android demonstration | [pre-merge Android source](https://github.com/trimblemitch796-cell/SYNTH_SHAI/tree/f3f219769634efc485b87ac1fbd027ef326201f9/android-app) | Earlier fixed scripted replies and written practice. This is not the current main Android response path. |
| Scripted Linux CLI and historical Android instructions | [main build matrix](https://github.com/trimblemitch796-cell/SYNTH_SHAI/blob/main/android-app/BUILD_MATRIX.md) | The CLI still uses the scripted engine. Older Android instructions do not describe the current local-model app; use the local-chat review above. |
| Local Qwen Android research | [research/android-local-qwen-chat](https://github.com/trimblemitch796-cell/SYNTH_SHAI/tree/research/android-local-qwen-chat) | Earlier local-model research branch. Main now contains consolidated local chat through PR #115; this branch is not the current 0.3.4 source. |
| Native model-load diagnostics | [research/android-qwen-v031-load-diagnostics](https://github.com/trimblemitch796-cell/SYNTH_SHAI/tree/research/android-qwen-v031-load-diagnostics) | Separate diagnostic research branch, not a production release or proof that model loading works on every phone. |
| Offline synthetic worker boundary research | [draft PR #112](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/112) | Content binding in a synthetic worker. Not complete OS isolation or deployment approval. |
| Protected staging chat clients | [draft PR #113](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/113) | Staging-client research; distinct from offline on-device inference. |
| Google-to-mocked-chat contract | [draft PR #114](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/114) | Offline integration tests with mocks, not verified live Google sign-in or a deployed chat service. |

### Important Android navigation warning

Main now includes PR #115 at merge commit `d1091d3ed861d0eff6e989b8caa4e2a5cde975c0`. Its [Gradle configuration](https://github.com/trimblemitch796-cell/SYNTH_SHAI/blob/main/android-app/app/build.gradle.kts) identifies `0.3.4-screen-state`, version code `10`, package `org.tuuwanasavi.synthshai.localchat.diagnostics`, and ARM64 phone builds (x86_64 is available for emulator CI). Merging source does not install or certify a phone update.

Older scripted-demo `android-app/README.md` and `BUILD_MATRIX.md` content remains historical documentation, including on the diagnostic branch. **Do not use it to describe the current main Android response path.**

The diagnostic branch's [Gradle configuration](https://github.com/trimblemitch796-cell/SYNTH_SHAI/blob/research/android-qwen-v031-load-diagnostics/android-app/app/build.gradle.kts) identifies `0.3.0-local`, version code `7`, package `org.tuuwanasavi.synthshai.localchat`, and `arm64-v8a`. The branch name contains “v031”, but that is not its embedded APK version. Identify a build by its exact source commit, artifact checksum and signing identity, not by its filename or branch name alone.

The current generated-response path has no wired generated-output safeguard. Old scripted safety tests do not validate Qwen responses, and independent security/USHAI verification remains unestablished. Emulator inference and persistence smoke checks are integration evidence, not general accuracy or safety certification. Screen locking/backgrounding can still interrupt generation; recent saved chat is bounded, not permanent learning.

A GGUF model file is separate from the APK. Selecting a file, verifying its bytes, successfully loading the native engine, and generating a response are distinct checks. A local response does not by itself prove factual accuracy, durable memory, ongoing training, consciousness or complete network isolation.

## Pull requests are not interchangeable copies

As checked on 16 November, the following Google-backend reviews form a stack through their base/head branches:

`#98 → #100 → #101 → #102 → #105 → #106 → #114`

The Android identity-contract review has a separate stack: `#103 → #104`.

Do not delete branches or close these PRs merely because their contents overlap. Review dependencies and unique changes first. Open PRs, including apparently mergeable ones, are not merged or approved releases.

## Safe cleanup order

1. Keep this navigation map separate from implementation and historical evidence.
2. Reconcile branch-specific Android instructions and version labels in a later documentation review.
3. Record exact source revision, test command, result, environment and limitations for each artifact.
4. Review branch/PR dependencies before proposing any archival, closure, deletion or merge.
5. Preserve existing human-approval requirements and all `144 HOLD` boundaries.

This map makes no changes to runtime code, build configuration, permissions, deployment, existing README content or safety controls. No new tests or independent validation are claimed.
