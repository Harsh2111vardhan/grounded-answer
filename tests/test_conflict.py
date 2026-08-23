from src.grounding.conflict import ConflictChecker
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


def test_same_clause_does_not_conflict():
    checker = ConflictChecker()

    clause = make_evidence(
        "§1.1.1",
        "A recipient must report a change within 10 days.",
    )

    result = checker.check(clause, clause)

    assert result.conflict is False


def test_different_deadlines_are_detected_as_conflict():
    checker = ConflictChecker()

    clause_a = make_evidence(
        "§4.3.2",
        "A recipient must report a change of circumstances "
        "within 10 calendar days.",
    )

    clause_b = make_evidence(
        "§9.1.4",
        "A recipient must report a change of circumstances "
        "within 30 calendar days.",
    )

    results = checker.check_all(
        "What is the reporting deadline for a change of circumstances?",
        [clause_a, clause_b],
    )

    assert len(results) == 1
    assert results[0].conflict is True
    assert results[0].clause_a == "§4.3.2"
    assert results[0].clause_b == "§9.1.4"


def test_unrelated_deadline_difference_is_not_conflict():
    checker = ConflictChecker()

    clause_a = make_evidence(
        "§5.2.1",
        "A household member who is temporarily absent "
        "remains a household member for the first 28 days "
        "of the absence.",
    )

    clause_b = make_evidence(
        "§5.2.2",
        "The period in §5.2.1 is extended to 90 days "
        "where the absence is for a qualifying reason.",
    )

    results = checker.check_all(
        "Does the number of contact hours determine whether "
        "an enrolment qualifies as full-time?",
        [clause_a, clause_b],
    )

    assert results == []


def test_full_time_question_does_not_trigger_absence_conflict():
    checker = ConflictChecker()

    full_time = make_evidence(
        "§1.4.6",
        "Full-time student means a person enrolled in a course "
        "of study at an accredited institution of higher education, "
        "where the institution classifies the enrolment as full-time. "
        "Enrolment status is determined by reference to the "
        "institution's own classification and not by the number "
        "of contact hours.",
    )

    absence_a = make_evidence(
        "§5.2.1",
        "A household member who is temporarily absent from the "
        "household address remains a household member for the "
        "first 28 days of the absence.",
    )

    absence_b = make_evidence(
        "§5.2.2",
        "The period in §5.2.1 is extended to 90 days where the "
        "absence is for a qualifying reason.",
    )

    results = checker.check_all(
        "Does the number of contact hours determine whether "
        "an enrolment qualifies as full-time?",
        [full_time, absence_a, absence_b],
    )

    assert results == []


def test_identical_deadlines_are_not_conflict():
    checker = ConflictChecker()

    clause_a = make_evidence(
        "§2.1.1",
        "A report must be submitted within 10 calendar days.",
    )

    clause_b = make_evidence(
        "§2.1.2",
        "The notice must be given within 10 calendar days.",
    )

    results = checker.check_all(
        "What is the deadline for submitting the report?",
        [clause_a, clause_b],
    )

    assert results == []