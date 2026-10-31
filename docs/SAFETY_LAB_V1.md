# SHAI Safety Lab V1 — offline synthetic demonstration

Run from the repository root after installing the pinned dependencies:

```bash
python -m safety_lab_demo
python -m unittest test_safety_lab_demo -v
python -m unittest discover -q
```

The demo exercises the existing `verification_v3_1.verify_once` gate with two disposable, locally generated Ed25519 test keys and a temporary SQLite database.

Expected decisions:

| Synthetic case | Expected result |
| --- | --- |
| Missing signed evidence | `144 HOLD` |
| Valid signed evidence | `REVIEW_REQUIRED` |
| Reused challenge | `144 HOLD` |

The CLI exits nonzero if any decision differs. The output explicitly reports `approval_granted: false`.

**Security boundary:** This is a teaching and regression demonstration, not proof of production security, independent verification, operator authentication or deployment approval. It performs no network calls or real-world actions, and stores no persistent private keys. The use of local replay storage does not solve multi-device replay. Only the exact revision tested should be described as passing.
