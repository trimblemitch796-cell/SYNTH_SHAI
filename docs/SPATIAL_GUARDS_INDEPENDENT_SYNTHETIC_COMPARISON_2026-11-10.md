# Safe independent comparison note — SYNTH_SHAI / Spatial Guards
**10 November 2026 — research-only; 144 HOLD**

This note offers our independently authored *synthetic* boundary cases for peer discussion. It does not reproduce any third-party private test fixture, proprietary implementation or clinical data.

| Generic concern | Native SYNTH_SHAI test evidence | Limitation for comparison |
|---|---|---|
| Benign read action | Signed `READ` is refused with `144 HOLD` | Not comparable to a clinical READ; this worker only supports `synthetic_review` |
| Unauthorized write | Signed `WRITE` is refused with `144 HOLD` | No session mutation state machine or WRITE pathway is implemented |
| Unknown action | Signed unknown custom intent is refused with `144 HOLD` | There is no `UNDETERMINED` human escalation queue |
| Encoded example marker | Declared bounded encoding is decoded, hashed and compared before signed dispatch; illustrative marker refused, including tested compatibility, control and combining-mark variants | Synthetic marker is **not** patient-data leak prevention or arbitrary encoding detection |
| Review vs. execution | Correctly signed test-only request returns `SIMULATED_REVIEW_ONLY` once; replays HOLD | No authenticated human review or real command execution exists |

**Evidence checkpoints:** exact GitHub PR head SHA; both Python CI jobs; negative-path results; any fixture discrepancy; replay-store side effects; whether a result is a hard block, simulated approval, actual human referral, or tool execution. The previous verified baseline was `6e9765dd` (742/742 each on Python 3.11 and 3.13). New cases must be confirmed by fresh CI before reporting them as passed.

**Review questions for independent comparison (not accusations about either system):**
1. Does policy inspection run on decoded content for **all** allowed actions, including read-only ones, before any allow decision?
2. Is a session transition lock authenticated, bound to the intended session/turn and unusable by request-supplied state?
3. Are unknown and malformed actions conservatively blocked while being separately counted for human review, without silently claiming a real review queue exists?
4. Are decoding declarations, raw representations, maximum depth, Unicode folding, timeouts and replay semantics explicitly specified in a versioned contract?
5. Can both systems report the same synthetic cases and measurement scope without equating an in-process latency microbenchmark to end-to-end execution security?

**Safety and evidence limits:** The public PR contains **only our own synthetic cases**. This document is not an independent audit or a measured test result from Spatial Guards. Research PR remains DRAFT, not merged and not deployed. **144 HOLD**.
