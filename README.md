# SYNTH_SHAI
def verify_result(result):
    required = (
        "test_report",
        "source_revision",
        "verification_evidence",
    )

    if not all(result.get(k) for k in required):
        return "144 HOLD"

    return "REVIEW_REQUIRED"