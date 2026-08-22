from src.grounding.conflict import (
    ConflictChecker,
    _potential_conflict_pair,
)
from src.models import Evidence


def clause(clause_id, text):
    return Evidence(
        clause_id=clause_id,
        text=text,
        part="Part 1",
        section="1.1",
        line_no=1,
        retrieval_sources=["semantic"],
    )


def test_detects_different_deadlines():
    checker = ConflictChecker()

    result = checker.check(
        clause(
            "§4.3.2",
            "A recipient must report a change within 10 calendar days.",
        ),
        clause(
            "§9.1.4",
            "A recipient must report the same change within 30 days.",
        ),
    )

    assert result.conflict is True
    assert result.clause_a == "§4.3.2"
    assert result.clause_b == "§9.1.4"


def test_same_deadline_is_not_conflict():
    checker = ConflictChecker()

    result = checker.check(
        clause(
            "§4.3.2",
            "A recipient must report a change within 10 days.",
        ),
        clause(
            "§9.1.4",
            "The recipient must report the change within 10 days.",
        ),
    )

    assert result.conflict is False


def test_unrelated_clauses_are_not_candidates():
    assert not _potential_conflict_pair(
        clause(
            "§1.4.6",
            "Full-time student means enrolment classified as full-time.",
        ),
        clause(
            "§5.4.1",
            "Care allowance is disregarded in the calculation.",
        ),
    )


def test_related_clauses_are_candidates():
    assert _potential_conflict_pair(
        clause(
            "§4.3.2",
            "A recipient must report a change within 10 days.",
        ),
        clause(
            "§9.1.4",
            "A recipient must report the same change within 30 days.",
        ),
    )


def test_check_all_finds_conflict_without_api():
    checker = ConflictChecker()

    results = checker.check_all(
        [
            clause(
                "§1.4.6",
                "Full-time student means enrolment classified as full-time.",
            ),
            clause(
                "§4.3.2",
                "A recipient must report a change within 10 days.",
            ),
            clause(
                "§9.1.4",
                "A recipient must report the same change within 30 days.",
            ),
        ]
    )

    assert len(results) == 1
    assert results[0].conflict is True