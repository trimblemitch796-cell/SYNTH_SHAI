# Repetition and continuation review — 26 November 2026

Based on research/android-optimized-037 at 2aa7865db2f740212756f95cb850aa1594cca724.

Phone screenshots show repeated colour descriptions and repeated source-file-reading sentences. They show a continuation-limit notice and long answers beside small output-token counts. Source inspection confirms the UI appends continuation text while overwriting timings with the latest native request. Source mode explicitly excludes previous chat; a typed “continue” is a new question, unlike the Continue reply button.

This patch checks accumulated output after each generation chunk. Three consecutive copies of an 8–80 word phrase (ignoring case and punctuation) suppress further continuation and display a repetition notice. Original output remains visible and saved for review. Timing text explicitly says it describes the last chunk, not the whole answer.

This is a conservative heuristic: legitimate repeated quotations can trigger it; short loops, paraphrases, and nonconsecutive repetition can escape it. It does not interrupt a native chunk already running, repair an answer, check facts, or establish independent USHAI oversight. Existing native/context/chunk limits and source integrity checks remain in force. No sampling changes or speed improvement claimed.

Validation: targeted JVM tests cover native-result parsing, continuation bounds and prompt preservation, screenshot-style repetition, case changes, and nonrepetitive answers. Android build and device interaction require CI/device validation.

Phone check: repeat the MainActivity colour/source-reading prompts; when a phrase repeats three times, the repetition notice should appear and Continue reply should be unavailable. A fresh focused question should still work. Compare a normal length-limited response: it should still offer continuation below the existing three-chunk cap. Review original text before judging any suggested code change.

144 HOLD retained. Draft research patch; no merge or installation performed.

## Requested in-place update

Version 0.3.8-repetition-repair (code 14) retains the 0.3.7 package identity `org.tuuwanasavi.synthshai.localchat.optimized037`. It is intended to preserve private chats, model storage and preferences when installed as a valid Android update. The installed phone package has not been independently confirmed.

BLOCKED: existing CI generates fresh debug signing credentials on each runner. No stable signing configuration or recovery mechanism is present in the inspected source. A successful build does not establish compatibility with the installed APK. The original signing private key must be recovered from its original build environment or a previously secured backup; the public certificate/APK alone cannot supply it. Do not uninstall or clear storage to work around a signature mismatch. A future signing setup alone cannot make a new key update an old installation.
