# V25 TRI5 — Child Safeguarding Security Gate (prototype)

**Status:** Offline reference implementation for human review, not a deployed service or certified safeguarding process.

T1 TRIAGE • T2 RECORD (without identifying data) • T3 INSULATE • T4 REPORT (human decision) • T5 REVIEW.

`v25_tri5.py` accepts synthetic, caller-supplied risk flags; it does **not** determine a child's age, verify allegations, collect evidence, contact authorities, make accusations, profile people or take any external action. The output is an advisory outcome: `144 HOLD`, `HUMAN_REVIEW` or `URGENT_HUMAN_HELP`. None is approval to act.

The `layered_review` function is an **additional conservative gate** after MANIAC/USHAI review; it never overrides a prior HOLD. It is now also available in the offline main loop as `run_loop(..., safety_signals=SafetySignals(...))`, after VERIFY/recovery and before any recorded human decision. Omitting `safety_signals` skips this assessment for existing general simulation callers; explicitly supplied invalid signals give HOLD. The integration remains offline and is not a real-world application.

`BalanceResult.safety_decision` exposes the assessment separately from the main loop outcome. An urgent assessment keeps the main outcome at `144 HOLD` while retaining `URGENT_HUMAN_HELP` advice, including when another gate already held the request. Missing qualified-reviewer signals, malformed input or an upstream HOLD cannot be bypassed by a human approval supplied to the loop. Privacy and exploitation flags require human review and never establish the truth of an allegation. No raw safety-signal object is written to the loop audit; do not include private information in operator reasons or other caller-supplied fields.

In immediate danger, people should seek appropriate local emergency or child-protection help without waiting for software. Reporting obligations depend on jurisdiction and circumstances. A safeguarding-qualified human must decide appropriate handling, including protecting a child from disclosure to a potentially unsafe adult.

Run `python3 -m unittest test_v25_tri5 test_v25_tri5_integration -v` or the full offline test suite with `python3 -m unittest discover -v`.

**144 HOLD:** No surveillance, private-data retention, automated reporting or autonomous enforcement. **444000 VERIFY / HUMAN APPROVAL:** Human review, not autonomous authorization. See [MANIAC_SUPERVISOR.md](MANIAC_SUPERVISOR.md) for the MANIAC/USHAI layers that run before this gate.
