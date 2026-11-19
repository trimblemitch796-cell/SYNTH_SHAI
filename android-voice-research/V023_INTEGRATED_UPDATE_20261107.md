# SYNTH_SHAI Android V0.2.3.1 — integrated offline review build

**Review only. No merge, service deployment, internet access, OpenAI API calls or live Android sign-in. 144 HOLD remains active.**

This branch starts at the current draft Emerald Tablet lesson PR #95, which stacks the history-vs-story regression from draft PR #94 onto Android V0.2.3. It additionally incorporates the offline-only Kotlin PKCE preflight source, tests and review handoff from draft PR #93.

## Bounded contents

- Existing V0.2.3 Vietnamese written-mark and scripted chat demonstration.
- Whole-word story/stories routing to avoid treating "history" as "story".
- Fixed four-stage Emerald Tablet historical/source lesson (not AI inference, browsing or independent manuscript verification).
- PKCE S256, random state + nonce, exact HTTPS redirect/state matching, 5-minute one-use pending transaction with failure/replay rejection. **There is no Android sign-in UI, provider, app-link binding, network permission or token exchange.**
- Emulator test now checks the actual text inserted by adb before sending; it retries once if the emulator keyboard corrupts characters instead of accidentally sending an unintended input.
- versionCode 6, versionName "0.2.3.1" to identify this distinct test APK. **Debug APK replacement is not assured**: GitHub build runners can use separate debug signing identities, so Android may require the operator to uninstall the older debug build before installing the new one. Never uninstall without checking that locally held app data or settings are backed up. This offline app's documented history is only in memory.
- No API key embedded. No host process, autonomous agent, shell, camera, mic, contact, money or messaging actions. The AndroidManifest still excludes INTERNET permission.

## Validation required

1. Check exact HEAD CI: Android debug APK/JUnit, Linux Android dual build, emulator UI smoke, repo verification, CATHARSIS, release security.
2. Inspect emulator evidence if smoke fails; a passing JVM test does not replace device observation.
3. Obtain correct exact-commit debug APK from GitHub Actions, confirm its SHA256 hash, and run a careful user-authorized physical Android smoke check.
4. **Do not merge** PR #93, #94, #95 or this integrated review simply to ship a live login; the code does not implement one. Future integration requires a vetted OIDC provider, Android verified App Links, provider response validation, session-issuer exchange and independent technical review.
5. Do not attach Render or deploy a server. Consequential use remains **144 HOLD**.

## Source branches

- Base: review/android-v023-vietnamese-written-marks-20261106
- Regression: review/android-v023-emerald-history-regression-20261107, draft PR #94
- Lesson: review/android-v023-emerald-tablet-lesson-20261107, draft PR #95
- PKCE preflight: review/android-pkce-login-preflight-20261106, draft PR #93
