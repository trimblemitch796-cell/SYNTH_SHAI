# Android V0.2.3 — bounded Emerald Tablet lesson

**Created 7 November 2026.** Created by Mitchell John Eric Trimble with AI assistance.
**Review-only teaching patch. Consequential operations remain at `144 HOLD`.**

## Intended offline teaching behaviour
- `Emerald Tablet`, `Teach me the Emerald Tablet`, the agreed eight-line paraphrase, or a question explicitly naming the Emerald Tablet enters a *fixed, four-part* lesson.
- `tell me more` / `more please` advances SOURCE → TEXT → SYMBOLISM → VERIFY, then ends. Restart with `Emerald Tablet`.
- SOURCE: this is a historical alchemical work transmitted in medieval Arabic and Latin traditions, traditionally attributed to Hermes Trismegistus. The attribution is not an authenticated author identification.
- TEXT: common versions include above/below, one source, Sun/Moon/wind/Earth, separation, ascent/descent. The user-supplied English lines are a paraphrase, not a diplomatic translation or direct manuscript transcription. Versions vary.
- SYMBOLISM: correspondence and transformation are interpretive categories; these metaphors are not evidence of a physical cosmic law.
- VERIFY: manuscripts and translations can be historically studied, but metaphysical assertions cannot be promoted to scientific facts merely because the text says them.
- The app **does not browse**, inspect actual manuscripts or translate unseen tablets. These are preset responses, **not model training, permanent knowledge acquisition, autonomous reasoning, a hosted backend or independent validation**.

## Historical reference material
- University of Oxford Cabinet, *The Emerald Tablet of Hermes Trismegistus* — historical Arabic manuscript tradition and attribution: https://www.cabinet.ox.ac.uk/emerald-tablet-hermes-trismegistus
- University of Oxford Newton Project, *Translation and transcription of the Tabula Smaragdina*, ALCH00017 — Newton's English/Latin reception, c. 1680s-1690s: https://newtonproject.ox.ac.uk/catalogue/record/ALCH00017
- *The Emerald Tablet and the Origins of Chemistry*, Arundel MS 164 Latin transcription and textual note — useful comparison of medieval text wording; a secondary treatment: https://www.medievalists.net/2023/04/the-emerald-tablet-and-the-origins-of-chemistry/

These sources provide historical context; they are **not directly queried at runtime**, nor has this app independently collated manuscript witnesses.

## Regression and review evidence
A focused *local Kotlin/JVM* smoke harness containing the eight-line question, four-step lesson, quiz switching, history-vs-story, normal story and Vietnamese, explicit action HOLD and unrelated-text checks passed **13/13** while the change was being prepared. This is project-maintained offline testing, not proof of the final GitHub head's Android APK. A separate **exact-head** Android JUnit, emulator smoke, APK build, Linux CLI and repository verification run must complete before any merge decision.

The previous PR #94 regression deliberately expected a fallback for the full Emerald prompt before this explicit teaching feature. It is updated to expect the opt-in, bounded SOURCE → TEXT response; the separate check that plain `history` must not trigger preset `story` remains.

## Boundaries
No new Android permissions, microphones, Internet, credentials, model calls, account integration, external actions, operating-system isolation claims, automatic merges or deployments. No claim to verify primary historical witnesses. **144 HOLD remains.**
