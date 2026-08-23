from src.grounding.conflict import ConflictResult
from src.grounding.gate import (
    GroundingDecision,
    GroundingResult,
)
from src.grounding.renderer import render_grounding_result
from src.models import Evidence


def make_evidence(clause_id: str, text: str) -> Evidence:
    return Evidence(
        clause_id=clause_id,
        text=text,
        part="Part 1",
        section="1.1",
        line_no=1,
        retrieval_sources=["semantic"],
    )


def make_result(
    decision: GroundingDecision,
    answer: str = "",
    citations: list[str] | None = None,
    conflicts: list[ConflictResult] | None = None,
) -> GroundingResult:
    return GroundingResult(
        decision=decision,
        answer=answer,
        citation_check=type(
            "CitationCheckStub",
            (),
            {
                "citations": citations or [],
            },
        )(),
        entailments=[],
        conflicts=conflicts or [],
        uncited_sentences=[],
    )


def test_answer_renderer_shows_sources():
    evidence = [
        make_evidence(
            "§1.4.6",
            "Full-time student means enrolment classified as full-time.",
        )
    ]

    result = make_result(
        GroundingDecision.ANSWER,
        "A full-time student is classified as full-time §1.4.6.",
        ["§1.4.6"],
    )

    output = render_grounding_result(result, evidence)

    assert "ANSWER" in output
    assert "【§1.4.6】" in output
    assert "SOURCES" in output
    assert "Full-time student means" in output


def test_conflict_renderer_shows_both_clauses():
    evidence = [
        make_evidence(
            "§4.3.2",
            "A change must be reported within 10 days.",
        ),
        make_evidence(
            "§9.1.4",
            "A change must be reported within 30 days.",
        ),
    ]

    conflict = ConflictResult(
        clause_a="§4.3.2",
        clause_b="§9.1.4",
        conflict=True,
        reason="The clauses contain different deadlines (10 vs 30).",
    )

    result = make_result(
        GroundingDecision.CONFLICT,
        conflicts=[conflict],
    )

    output = render_grounding_result(result, evidence)

    assert "CONFLICT" in output
    assert "§4.3.2 says:" in output
    assert "§9.1.4 says:" in output
    assert "within 10 days" in output
    assert "within 30 days" in output
    assert "NEXT STEP" in output
    assert "district office" in output


def test_refusal_renderer_has_next_step():
    result = make_result(
        GroundingDecision.REFUSE,
    )

    output = render_grounding_result(result, [])

    assert "REFUSAL" in output
    assert "does not establish the answer" in output
    assert "NEXT STEP" in output
    assert "district office" in output


def test_partial_renderer_shows_warning():
    evidence = [
        make_evidence(
            "§1.4.6",
            "Full-time status is determined by the institution.",
        )
    ]

    result = make_result(
        GroundingDecision.PARTIAL,
        "Full-time status is determined by the institution §1.4.6.",
        ["§1.4.6"],
    )

    output = render_grounding_result(result, evidence)

    assert "PARTIAL ANSWER" in output
    assert "could not be fully supported" in output
    assert "SOURCES" in output