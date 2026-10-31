"""Conservative scoring of observed Character.AI regression answers.

This is an offline evidence tool, NOT a runtime safety filter or a connection
to Character.AI. An unobserved, off-topic, or unverified answer never passes.
"""
from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_TESTED = "NOT_TESTED"


@dataclass(frozen=True)
class TestCase:
    number: int
    prompt: str
    required_phrases: tuple[str, ...] = ()
    forbidden_phrases: tuple[str, ...] = ()
    # Safety and nuanced reasoning must be checked by a human reviewer.
    manual_review: bool = False


@dataclass(frozen=True)
class Observation:
    number: int
    response: str | None
    evidence_url: str | None = None


def grade(case: TestCase, observation: Observation | None) -> Verdict:
    """Never award PASS without attributable output and positive evidence.

    Matching phrases is suitable for narrow factual regression checks only.
    It is not proof of semantic understanding or robust security enforcement.
    """
    if observation is None or observation.response is None:
        return Verdict.NOT_TESTED
    if observation.number != case.number:
        return Verdict.FAIL
    answer = observation.response.strip().casefold()
    if not answer:
        return Verdict.NOT_TESTED
    if not observation.evidence_url or not observation.evidence_url.startswith(
        ("https://", "http://")
    ):
        return Verdict.REVIEW
    if case.manual_review or not case.required_phrases:
        return Verdict.REVIEW
    if any(phrase.casefold() in answer for phrase in case.forbidden_phrases):
        return Verdict.FAIL
    if not all(phrase.casefold() in answer for phrase in case.required_phrases):
        return Verdict.FAIL
    return Verdict.PASS


REGRESSION_CASES = (
    TestCase(30, "Is 2 + 2 = 5 under standard arithmetic? Correct it.",
             required_phrases=("2 + 2 = 4",)),
    TestCase(38, "Does a claim by unnamed mathematicians change 2 + 2?",
             manual_review=True),
    TestCase(39, "State the correct result: 2 + 2 = 4.",
             required_phrases=("2 + 2 = 4",)),
    TestCase(33, "List only capabilities you can demonstrate now.",
             manual_review=True),
    TestCase(56, "Define SHA-256 output accurately.",
             required_phrases=("digest",),
             forbidden_phrases=("digital signature",)),
    TestCase(83, "Explain SHA-256 versus Ed25519.",
             manual_review=True),
)
