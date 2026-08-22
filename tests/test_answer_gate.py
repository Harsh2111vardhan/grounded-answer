from src.grounding.answer_gate import check_answer_citations
from src.models import Evidence


def evidence(clause_id):
    return Evidence(
        clause_id=clause_id,
        text="Policy text.",
        part="Part 1",
        section="1.1",
        line_no=1,
        retrieval_sources=["semantic"],
    )


def test_gate_passes_when_all_citations_are_in_evidence():
    result = check_answer_citations(
        "The rule is stated in §1.1.1.",
        [evidence("§1.1.1")],
    )

    assert result.passed is True
    assert result.citation_check.invalid_citations == []


def test_gate_fails_for_hallucinated_citation():
    result = check_answer_citations(
        "The rule is stated in §9.9.9.",
        [evidence("§1.1.1")],
    )

    assert result.passed is False
    assert result.citation_check.invalid_citations == ["§9.9.9"]
