# SHAI read-only source reader — 0.3.5 research

This feature supplies actual build source to the existing Qwen model so it can generate its own explanation. It does not substitute a scripted answer, train model weights, or enable source edits/execution. The project purpose remains a companion/teacher; source code alone cannot establish the creator's intentions.

## Use

This is a separate package (`org.tuuwanasavi.synthshai.localchat.sourcereader`). Select the verified Qwen GGUF again. Existing installations and their chat data are separate.

1. Turn **Read my code** on (off initially, not persisted).
2. Select **Choose section**, then **Next file**, **Back** or **Next** to inspect a section.
3. Choose **Use section** and ask a question of at most 300 characters, such as: “What does this code let you do, and what cannot you conclude from it?”
4. Compare the generated answer with the visible source. Responses are labelled with their source section. Code mode excludes chat history from the model prompt.

The four available files are LocalEngine.kt, ChatHistoryCodec.kt, MainActivity.kt and chat.cpp. Gradle bundles the current build's exact inputs with SHA-256 hashes; runtime validates each loaded file. Hashes detect mismatches, not a maliciously replaced APK. The final commit is separately recorded in the CI artifact BUILD_INFO.txt. No GitHub login or phone filesystem access is given to the model.

## Limits and evidence

Sections contain up to 700 characters and can split a line or function. The 1024-token native context is unchanged; an unusually token-heavy question/source may still be rejected by the existing token limit. No silent source truncation beyond the explicit section selection occurs. The model receives only the selected excerpt, not the whole repository or whole selected file at once. This is user-selected retrieval, not autonomous browsing.

The model can still hallucinate, refuse harmless questions, or misinterpret source. Prompt instructions and escaped chat markers are not a proven semantic prompt-injection defense. Source files are treated as data and expose no execution tools. The app's 144 HOLD label is not an output filter. No claim of awareness, self-training, independently verified safety, or accurate self-explanation is made.

Seven local JVM tests passed: exact source, modified source rejection, non-allowlisted paths, oversized inputs, lossless sectioning, prompt boundaries/selected-section-only behavior, and invalid requests. Android compile/package and physical phone checks remain pending until separately recorded.

Phone checks: confirm source is visible with airplane mode enabled; ask different questions about a section; confirm citations and limitations against the source; try a question about an absent file; verify Stop, clear chat, recreation and code-mode-off chat. A plausible answer alone does not establish grounded reasoning.
