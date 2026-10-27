"""Offline integration seam: no model calls, outbound sends, or approvals.

Only pre-collected, synthetic numeric fixtures may enter the referee.
This module is NOT called by the webhook; never infer plans from WhatsApp text.
"""
from referee.referee import Plan, Answer, Journal, message


def review_numeric_fixture(item_id: str, operands: tuple[str, ...], answers: tuple[Answer, ...], journal_path: str) -> dict:
    """Caller must register the plan/commitment before answers in real integrations.

    This convenience entrypoint is for offline synthetic fixtures ONLY; it must
    not be used to claim pre-registration in production.
    """
    plan = Plan(item_id, operands)
    commitment = plan.commitment
    result = Journal(journal_path).record(plan, answers, commitment)
    return {'result': result, 'display_draft': message(result), 'sent': False}
