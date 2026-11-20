# Human-reviewed local Qwen voice experiment 0.9

This document describes the 0.9 entry point; CONFIRMED_REPLY_08.md and older copied documents describe historical builds.

Select the verified Qwen GGUF, tap Start, wait for Speak now, speak, then finish the phrase if necessary. Recognition stops before the editable transcript appears. Confirming that transcript submits its corrected text to local Qwen. The generated response is displayed with speech off. Approve displayed reply consumes a one-use permission to speak exactly that text. Tap Start for another independent turn. No conversation memory or automatic microphone restart is implemented.

Stop, backgrounding, timeouts, and a new session invalidate the pending review and token. Native generation receives cancellation; a new inference cannot start until the prior worker releases resources. Late callbacks cannot restore approval. The UI distinguishes preparing/generating from completed output. A separate fixed speech diagnostic and fixed 2+2 model test remain available.

This is an explicit human-reviewed research path alongside the unchanged fail-closed UshaiVoicePolicy. Human input/output review is not evidence of automated content safety, child suitability, or correctness. No classifier or external action executor has been added. The app has no INTERNET permission and requests on-device recognition and installed non-network TTS; physical-device offline behavior still requires verification.

The separate package org.tuuwanasavi.synthshai.localchat.reviewedqwen09 preserves the installed 0.8 test and original chat app. Select the existing model file again; the new app verifies/imports its own private copy. Do not uninstall existing apps. Debug signer continuity is not assumed.

Validation: ReviewedTurn tests cover both review boundaries, one-shot speech, invalid content lengths, stale generation/completion callbacks, cancellation at all stages, and fresh confirmation on the next turn. Existing diagnostic tests remain. CI performs full Android compilation, unit tests, lint and native sanitizer checks. Phone checks must still cover audible approved output, Stop during generation/TTS initialization/playback, backgrounding, a second turn, and airplane mode with Wi-Fi/mobile data off.
