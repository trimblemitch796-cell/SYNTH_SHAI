# Reviewed Qwen voice 0.9.1 research update

Applies to the 0.9 reviewed Qwen voice app, retaining its package ID and incrementing versionCode to 7. Not merged or device-verified. 144 HOLD; human review is not automated content safety.

## Changes
- Optimize native inference with -O3 and retain verified model weights between foreground turns. Every request still verifies the private model file; contexts remain separate. Backgrounding and memory pressure request weight release.
- Report native end/limit/stopped and last-chunk load/setup/prompt/decode timing, token count, and cache reuse.
- Offer up to two manual continuations for length-limited replies. Preserve the confirmed question and accumulated answer; existing native context bounds reject oversized prompts. Continuation revokes speech eligibility until the new complete displayed answer is reviewed. Stop, timeout, backgrounding, new sessions and model selection revoke pending continuation.
- Generation deadline increases from 180 to 600 seconds per chunk. This does not itself accelerate inference. TTS playback deadline scales with approved text length, bounded to 330 seconds. Cancellation remains cooperative.

## Validation
119 platform-independent JVM tests passed, including 12 focused tests for review/continuation revocation, one-time playback, stale callbacks, malformed metadata, and bounded continuation prompts. Native cache address/undefined sanitizer check passed locally with leak detection disabled because this execution environment uses tracing; CI runs full sanitizers. Android-dependent GenerationExitInfo tests, Android build, lint, optimized compile-command verification and physical phone results are pending. Publishing the branch to GitHub was blocked by automatic approval review pending explicit destination-specific user approval; no remote build has been triggered.

## Signing and installation
The original workflow uses an ephemeral runner debug signing key. Keeping the package ID and increasing the version does not establish update compatibility. This workflow records the new APK certificate in SIGNER.txt. Compare against the installed APK certificate before installation; do not uninstall or clear existing app data to bypass a signature mismatch. No original private signing key has been recovered or changed. A persistent signing solution remains separate work if the old key is unavailable.

## Phone checks after compatible installation
Use airplane mode with Wi-Fi off and the existing verified Qwen GGUF. Confirm a short transcript, review the displayed answer, approve once and check audible output. Record cold and warm timings. Ask for a longer answer: when limit is reported, Continue must generate without speaking; review the accumulated answer before one playback. Exercise Stop and leaving foreground during generation/continuation and verify no late answer can be approved. Repeat speech approval taps must not replay. Report timings and any install error; do not remove the working app.

No measured speed gain, automated output safety, conversation memory, or real-world action capability is claimed.
