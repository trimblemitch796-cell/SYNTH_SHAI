# Confirmed fixed reply research 0.8

Based on the user-supplied 0.7 source archive, isolated from android-app.
Start recognition, wait for Speak now, speak, optionally Finish phrase, inspect the transcript, then tap Confirm transcript. One confirmation requests exactly one fixed speech fixture. Tap Start recognition for another turn. No automatic microphone restart.

Stop, backgrounding, starting another test, or clearing revokes the pending confirmation. Recognition confidence is diagnostic only for this manually confirmed fixed fixture. Qwen voice input/output policy is unchanged and remains blocked. Typed synthetic model probe remains separate. No transcript or audio persistence is added.

Eight new unit tests cover absent/invalid input, one-shot consumption, stale tokens, cancellation, fixed payload, and fresh turns. GitHub workflow runs all unit tests, native diagnostic tests, assembly, and lint. Device recognition, audibility and offline service behavior still require phone testing.

Uses separate package org.tuuwanasavi.synthshai.localchat.confirmedfixture because CI signing continuity with the installed research APK is not established. Installs alongside existing apps; no uninstall needed. Main local-chat package is unchanged.

Local verification: Kotlin 2.0.21 compilation and JUnit 4.13.2 execution passed 37 tests across ConfirmedFixedReply, VoiceLoop, ReplyPanel, RecognitionTiming and UshaiVoiceGate. Android Activity compilation, APK assembly and lint have not run. Publication was blocked by automatic approval review; no remote branch or CI run was created.
