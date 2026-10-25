# SYNTH_SHAI Super Tool V1 — Offline Starter

**Status:** Deterministic Python proof of concept. This is **not** a hosted AI application or a new AI/SI model.

## Three user-initiated modes
- **ASK:** Create a question/research brief for a human or future connected model. Does not fetch information or fabricate answers.
- **CHECK:** Record a claim and request evidence. Does not independently verify source truth.
- **BUILD:** Create a safe draft checklist. Does not run code, commit changes, operate hardware or send messages.

`super_tool_v1.run(mode, request, evidence=(), child_safety_concern=False)` returns an immutable `ToolResult`. Every outcome requires human review; `approval_granted` is always false. Unsupported operations, oversize/malformed inputs and reported safeguarding concerns produce `144 HOLD`.

V25 TRI5, MANIAC and USHAI are existing offline research modules; **this starter does not yet implement a validated end-to-end orchestrator or trained child-risk detection**. It will not monitor users or minors.

## Run
```sh
python -m unittest test_super_tool_v1 -v
```

## Next engineering milestones
1. Define validated trust boundaries and human-reviewed UX for ASK/CHECK/BUILD.
2. Build a genuinely integrated offline decision pipeline with explicit consent and typed evidence.
3. Test adversarial inputs and privacy; retain no private data by default.
4. Obtain independent security and child-safeguarding review before consequential deployment.

**144 HOLD on autonomous external actions. 444000 is human review, not approval.**
