# 0.3.7 optimized inference and bounded continuation

Motivation: user-provided phone screenshots show 358–836 seconds per reply, with model verification about one second. They do not isolate native loading, prompt processing or decoding. Code reading also produced incorrect explanations. Neither inference speed nor accuracy was established by prior green CI.

## Changes

- Compile native Debug C/C++ with `-O3 -g`, including fetched llama/ggml sources, while retaining existing architecture and model hash settings. CI inspects exported compile commands and fails if the effective final optimization option is not -O2/-O3. This tests a plausible speed cause; it is not a measured phone speedup.
- Per-request native result metadata separates load, setup/tokenization/context creation, prompt processing, and decoding durations. Show prompt/output token counts and whether model weights were reused. Errors still raise exceptions; Stop discards interrupted output. Timings exclude some teardown and wrapper overhead, so subphases need not equal total.
- Report natural end, 96-token limit or stopped status explicitly. A length-limit notice offers Continue reply. Continue reuses the original exact prompt/source and the accumulated assistant prefix, escapes chat control markers, and updates the same displayed/saved assistant message. No extra source selection or unrelated chat is substituted.
- At most two continuation requests (three chunks total). Native context limits remain authoritative; if the complete prefix cannot fit, return an error rather than silently dropping the question/source. New questions, source changes, model selection and clear chat revoke pending continuation. Pending continuation exists only in the current screen session; saved chat text remains after restart.
- Shorten source instructions to reduce irrelevant prompt text. Source sections remain 700 characters and may split functions; coherent function retrieval and reliable factual self-explanation remain unresolved. Responses are generated, not scripted.
- Install separately as SHAI 0.3.7 Repair Test, package suffix .localchat.optimized037, versionCode 13. Select the verified GGUF again. Preserve earlier apps/chats for comparison.

## Checks and limits

Local Kotlin unit checks cover metadata parsing/bounds, whitespace preservation, natural/stopped endings, original prompt retention, marker escaping and continuation bounds, plus existing source/history/model-store/reply regressions. Android/CI and phone results must be recorded separately. Native weights remain resident between foreground answers as in PR #122; background and memory-pressure release is cooperative.

Phone test: use identical source section, question and output budget in 0.3.6 and 0.3.7. Record cold/warm timing fields, charge state and whether the phone is hot. Test a naturally short answer, a long answer reaching the length limit, Continue, Stop during continuation, source changes, clear chat and restart. Continuation may itself end mid-sentence if its budget is reached, but the app must say why. Accuracy and physical-device speed remain unverified. 144 HOLD is retained as a research label, not a model-output safety filter.
