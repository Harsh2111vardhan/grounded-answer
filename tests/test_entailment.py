import pytest

from src.grounding.claims import Claim
from src.grounding.entailment import EntailmentChecker
from src.models import Evidence


class FakeGemini:
    def __init__(self, response):
        self.response = response

    def generate(self, prompt, system_instruction=None, max_output_tokens=200):
        return self.response


def make_clause():
    return Evidence(
        clause_id="§1.4.6",
        text=(
            "Full-time student means a person enrolled in a course of study "
            "at an accredited institution of higher education, where the "
            "institution classifies the enrolment as full-time."
        ),
        part="Part 1",
        section="1.4",
        line_no=42,
        retrieval_sources=["semantic"],
    )


def test_supported_claim():
    checker = EntailmentChecker(
        FakeGemini("YES\nThe clause defines full-time status by the institution.")
    )
    result = checker.check(
        Claim(
            text="A full-time student is classified as full-time by the institution.",
            citation="§1.4.6",
        ),
        make_clause(),
    )
    assert result.supported is True
    assert result.citation == "§1.4.6"


def test_unsupported_claim():
    checker = EntailmentChecker(
        FakeGemini(
            "NO\nThe clause does not say that students automatically receive assistance."
        )
    )
    result = checker.check(
        Claim(
            text="A full-time student automatically receives assistance.",
            citation="§1.4.6",
        ),
        make_clause(),
    )
    assert result.supported is False


def test_invalid_model_response_is_rejected():
    checker = EntailmentChecker(FakeGemini("Maybe"))
    with pytest.raises(ValueError, match="Expected YES or NO"):
        checker.check(
            Claim(
                text="A full-time student is classified by the institution.",
                citation="§1.4.6",
            ),
            make_clause(),
        )


def test_missing_evidence_fails_without_model_call():
    checker = EntailmentChecker(FakeGemini("YES"))
    result = checker.check_all(
        [Claim(text="Some claim.", citation="§9.9.9")],
        [make_clause()],
    )
    assert result[0].supported is False
    assert "not present" in result[0].reason
