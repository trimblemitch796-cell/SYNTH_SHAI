# V25 TRI5 — Child Safeguarding Security Gate (prototype)

**Status:** Offline reference implementation for human review, not a deployed service or certified safeguarding process.

T1 TRIAGE • T2 RECORD (without identifying data) • T3 INSULATE • T4 REPORT (human decision) • T5 REVIEW.

`v25_tri5.py` accepts synthetic, caller-supplied risk flags; it does **not** determine a child's age, verify allegations, collect evidence, contact authorities, make accusations, profile people or take any external action. The output is an advisory outcome: `144 HOLD`, `HUMAN_REVIEW` or `URGENT_HUMAN_HELP`. None is approval to act.

The `layered_review` function can be called as an **additional conservative gate** after MANIAC/USHAI review; it never overrides a prior HOLD. This is a library-level integration point, **not yet wired into a real-world application**.

In immediate danger, people should seek appropriate local emergency or child-protection help without waiting for software. Reporting obligations depend on jurisdiction and circumstances. A safeguarding-qualified human must decide appropriate handling, including protecting a child from disclosure to a potentially unsafe adult.

Run `python3 -m unittest test_v25_tri5 -v` or the full offline test suite with `python3 -m unittest discover -v`.

**144 HOLD:** No surveillance, private-data retention, automated reporting or autonomous enforcement. **444000 VERIFY / HUMAN APPROVAL:** Human review, not autonomous authorization. See [MANIAC_SUPERVISOR.md](MANIAC_SUPERVISOR.md) for the MANIAC/USHAI layers that run before this gate.
