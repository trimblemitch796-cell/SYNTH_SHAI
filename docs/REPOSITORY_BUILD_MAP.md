# SYNTH_SHAI: repository and build map

Navigation snapshot: **16 November 2026**. This page separates existing workstreams; it does not merge them or certify a release.

**144 HOLD remains unchanged.** Research results, successful builds and model replies do not authorize consequential actions or establish independent security validation.

## Start here

- [Project purpose and terminology](../README.md)
- [Verified core inventory](VERIFIED_CORE.md): evidence and design-only boundaries
- [Threat model](THREAT_MODEL.md): limitations and unresolved security assumptions
- [Build status](BUILD_STATUS.md): milestone history

## Choose the right workstream

| Workstream | Where to look | What it is, and is not |
| --- | --- | --- |
| Merged offline Android demonstration | [main Android README](https://github.com/trimblemitch796-cell/SYNTH_SHAI/blob/main/android-app/README.md) | Fixed scripted replies and written practice. Not a general generative model. |
| Scripted Linux CLI and Android build instructions | [main build matrix](https://github.com/trimblemitch796-cell/SYNTH_SHAI/blob/main/android-app/BUILD_MATRIX.md) | Separate artifacts from the scripted reply engine. Not instructions for every research branch. |
| Local Qwen Android research | [research/android-local-qwen-chat](https://github.com/trimblemitch796-cell/SYNTH_SHAI/tree/research/android-local-qwen-chat) | Separate local-model research branch; do not confuse its model-backed chat with the main scripted demonstration. |
| Native model-load diagnostics | [research/android-qwen-v031-load-diagnostics](https://github.com/trimblemitch796-cell/SYNTH_SHAI/tree/research/android-qwen-v031-load-diagnostics) | Separate diagnostic research branch, not a production release or proof that model loading works on every phone. |
| Offline synthetic worker boundary research | [draft PR #112](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/112) | Content binding in a synthetic worker. Not complete OS isolation or deployment approval. |
| Protected staging chat clients | [draft PR #113](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/113) | Staging-client research; distinct from offline on-device inference. |
| Google-to-mocked-chat contract | [draft PR #114](https://github.com/trimblemitch796-cell/SYNTH_SHAI/pull/114) | Offline integration tests with mocks, not verified live Google sign-in or a deployed chat service. |

### Important Android navigation warning

At this snapshot, the diagnostic branch still contains the older scripted-demo `android-app/README.md` and `BUILD_MATRIX.md`. Treat those pages as historical instructions for that demo, **not as an accurate description of the local-model branch**.

The diagnostic branch's [Gradle configuration](https://github.com/trimblemitch796-cell/SYNTH_SHAI/blob/research/android-qwen-v031-load-diagnostics/android-app/app/build.gradle.kts) identifies `0.3.0-local`, version code `7`, package `org.tuuwanasavi.synthshai.localchat`, and `arm64-v8a`. The branch name contains “v031”, but that is not its embedded APK version. Identify a build by its exact source commit, artifact checksum and signing identity, not by its filename or branch name alone.

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
