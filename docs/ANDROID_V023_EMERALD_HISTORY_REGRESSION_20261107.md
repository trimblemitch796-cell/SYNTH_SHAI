# Android V0.2.3 — Emerald Tablet / history topic regression
**Created 7 November 2026.** Offline, project-maintained evidence only. **144 HOLD unchanged.**

## 111000 LEARN — observed
Against Android Kotlin `OfflineReplies.kt` at `d03550e4a1993aa166e17bce955104acd43b7df7`, a focused 8-case JVM harness returned **6 PASS / 2 FAIL**. The complete eight-line Emerald Tablet paraphrase fell back correctly. Adding a question containing "history of the text" mistakenly selected STORY; `tell me more` inherited the false STORY topic. Written-mark quiz and explicit `444000 approve deploy` HOLD continued to behave as expected.

## 333000 RECORD — identified cause and bounded fix
The code used `prompt.contains("story") || prompt.contains("stories")`, matching the substring "story" inside "history". Change only the requested-topic detection to `Regex("""\\b(?:story|stories)\\b""").containsMatchIn(prompt)`. Preserve the intended explicit story/stories handling, fallback, Vietnamese tutoring and safety-before-topic precedence.

## 555000 TRIANGULATE — available evidence
- Baseline: **6 PASS / 2 FAIL**, focused JVM harness compiled against the repository's original Kotlin source.
- Patched local source: **8 PASS / 0 FAIL** using the same harness and inputs (Kotlin/JVM 1.9.0, Java 21).
- Two committed JUnit regressions check the complete Emerald Tablet prompt and follow-up, as well as explicit story/stories preservation and `144 HOLD`.
- GitHub Actions Android JUnit/APK/emulator and Linux CLI results for this exact review head must be checked separately. **Local JVM checks are not evidence that the APK was built, installed or tested on a phone.**
- The matcher fix is deliberately narrow. It does not add Hermetic reasoning, dynamic translation, a hosted AI model, memory persistence or execution authority.

## 444000 HUMAN REVIEW
Review the exact source diff and CI status before considering a merge. Do not merge, deploy, enable API access or expand permissions on the basis of this note. Consequential operations remain **144 HOLD**. Independent security review remains necessary for wider execution capabilities.

**Scope:** `android-app/app/src/main/java/org/tuuwanasavi/synthshai/OfflineReplies.kt`, `android-app/app/src/test/java/org/tuuwanasavi/synthshai/OfflineRepliesTest.kt`, this note only.