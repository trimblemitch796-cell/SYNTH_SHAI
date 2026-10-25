"""run_loop: Mitch's whole flow, end to end (offline simulation only).

  CHAIN (monitor -> evidence -> 555000 TRIANGULATE -> 444000 VERIFY)
    RISK / ERROR FOUND  -> 144 HOLD -> 1301133 REPAIR -> 666000 RECOVERY (optional)
    EVIDENCE SUFFICIENT -> HUMAN REVIEW (optional recorded human decision)
  then on both branches:
    222000 RE-OBSERVE -> 111000 COMPARE / LEARN -> 999000 AUDIT -> Δ BALANCE

Every gate decision is written to a hash-chained audit trail.
Returns (BalanceResult, AuditChain). BalanceResult is frozen; approval_granted is always False.
"""
from maniac.audit import AuditChain, verify_chain
from maniac.balance import close_loop
from maniac.chain import run_chain
from maniac.learn import LessonLog
from maniac.observe import reobserve
from maniac.recovery import recover, held_context, REPAIR, RECOVERY
from maniac.verify import HOLD, HUMAN_REVIEW

VERIFY = "444000 VERIFY / HUMAN APPROVAL"


def run_loop(supervisor, request, monitor, bundle, clock, *, expected_value,
             fresh_readings, recovery=None, human=None, lessons=None):
    """
    recovery: optional dict {"repair_note", "request", "bundle"} used only if
              the first pass ends in HOLD.
    human:    optional (operator_id, decision, reason) recorded only on HUMAN_REVIEW.
    fresh_readings: TRIANGULATE-format readings for 222000 RE-OBSERVE.
    """
    chain = AuditChain()
    lessons = lessons if lessons is not None else LessonLog()
    steps = []

    # CHAIN -> 444000 VERIFY
    result = run_chain(supervisor, request, monitor, bundle, clock)
    chain.append(VERIFY, result.decision, result.reasons)
    first_reasons = list(result.reasons)

    # HOLD branch: 144 HOLD -> 1301133 REPAIR -> 666000 RECOVERY
    if result.decision == HOLD:
        chain.append("144 HOLD", HOLD, result.reasons)
        if recovery is None:
            steps.append((RECOVERY, False, list(result.reasons)))
        else:
            ctx = held_context(request, bundle)
            result, note = recover(ctx, recovery.get("repair_note"), supervisor,
                                   recovery.get("request"), monitor, recovery.get("bundle"), clock)
            chain.append(REPAIR, "noted" if note else "refused",
                         "%s: %s" % (note.operator_id, note.reason) if note else result.reasons)
            chain.append(RECOVERY, result.decision, result.reasons)
            steps.append((RECOVERY, result.decision == HUMAN_REVIEW, list(result.reasons)))

    # HUMAN REVIEW branch: optional explicit human decision
    decision_record = None
    if result.decision == HUMAN_REVIEW and human is not None:
        try:
            decision_record = result.record_human_decision(*human)
            chain.append("HUMAN REVIEW", decision_record.decision, decision_record.reason)
        except (ValueError, TypeError) as exc:
            chain.append("HUMAN REVIEW", "refused", str(exc))
            steps.append(("HUMAN REVIEW", False, [("HUMAN REVIEW", str(exc))]))
        if decision_record is not None and not decision_record.approved:
            steps.append(("HUMAN REVIEW", False, [("HUMAN REVIEW", "human rejected")]))

    # 222000 RE-OBSERVE
    ok, why = reobserve(expected_value, fresh_readings)
    chain.append("222000 RE-OBSERVE", "match" if ok else "mismatch", why)
    steps.append(("222000 RE-OBSERVE", ok, why))

    # 111000 COMPARE / LEARN
    try:
        lessons.record(result.decision, HUMAN_REVIEW, "match" if ok else "mismatch",
                       first_reasons + list(result.reasons) + list(why), decision_record)
        chain.append("111000 COMPARE / LEARN", "recorded")
        steps.append(("111000 COMPARE / LEARN", True, []))
    except Exception as exc:  # fail closed
        chain.append("111000 COMPARE / LEARN", "failed", type(exc).__name__)
        steps.append(("111000 COMPARE / LEARN", False, [("111000 COMPARE / LEARN", "could not record")]))

    # 999000 AUDIT
    intact = verify_chain(chain.entries)
    chain.append("999000 AUDIT", "intact" if intact else "BROKEN")
    steps.append(("999000 AUDIT", intact, [] if intact else [("999000 AUDIT", "chain broken")]))

    # Δ BALANCE
    return close_loop(result.decision, steps, chain, decision_record), chain
