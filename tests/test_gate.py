from src.grounding.conflict import ConflictChecker
from src.grounding.entailment import EntailmentChecker
from src.grounding.gate import GroundingDecision, GroundingGate
from src.models import Evidence


def make_evidence(
    clause_id: str,
    text: str,
) -> Evidence:
    return Evidence(
        clause_id=clause_id,
        text=text,
        part="Part 1",
        section="1.1",
        line_no=1,
        retrieval_sources=["semantic"],
    )


class FakeEntailmentChecker:
    def __init__(self, results):
        self.results = results

    def check_all(self, claims, evidence):
        return self.results


class FakeConflictChecker:
    def __init__(self, results):
        self.results = results

    def check_all(self, question, evidence):
        return self.results


def test_no_evidence_refuses():
    gate = GroundingGate(
        FakeEntailmentChecker([]),
        FakeConflictChecker([]),
    )

    result = gate.evaluate(
        "Who qualifies?",
        "I don't know.",
        [],
    )

    assert result.decision == GroundingDecision.REFUSE


def test_relevant_conflict_takes_precedence():
    from src.grounding.conflict import ConflictResult

    evidence = [
        make_evidence(
            "§4.3.2",
            "A recipient must report a change within 10 days.",
        ),
        make_evidence(
            "§9.1.4",
            "A recipient must report a change within 30 days.",
        ),
    ]

    conflict = ConflictResult(
        clause_a="§4.3.2",
        clause_b="§9.1.4",
        conflict=True,
        reason="The clauses contain different deadlines (10 vs 30).",
    )

    gate = GroundingGate(
        FakeEntailmentChecker([]),
        FakeConflictChecker([conflict]),
    )

    result = gate.evaluate(
        "What is the reporting deadline for a change?",
        "The deadline is unclear §4.3.2.",
        evidence,
    )

    assert result.decision == GroundingDecision.CONFLICT
    assert len(result.conflicts) == 1


def test_unsupported_answer_refuses_without_conflict():
    from src.grounding.entailment import EntailmentResult

    evidence = [
        make_evidence(
            "§1.1.1",
            "The Department administers the program.",
        )
    ]

    entailment = EntailmentResult(
        claim="The Department pays every applicant.",
        citation="§1.1.1",
        supported=False,
        reason="The clause does not establish this claim.",
    )

    gate = GroundingGate(
        FakeEntailmentChecker([entailment]),
        FakeConflictChecker([]),
    )

    result = gate.evaluate(
        "Does every applicant receive payment?",
        "Every applicant receives payment §1.1.1.",
        evidence,
    )

    assert result.decision == GroundingDecision.REFUSE


def test_supported_answer_is_answer():
    from src.grounding.entailment import EntailmentResult

    evidence = [
        make_evidence(
            "§1.1.1",
            "A full-time student is classified by the institution.",
        )
    ]

    entailment = EntailmentResult(
        claim="A full-time student is classified by the institution.",
        citation="§1.1.1",
        supported=True,
        reason="The clause directly supports the claim.",
    )

    gate = GroundingGate(
        FakeEntailmentChecker([entailment]),
        FakeConflictChecker([]),
    )

    result = gate.evaluate(
        "Who determines full-time status?",
        "The institution determines full-time status §1.1.1.",
        evidence,
    )

    assert result.decision == GroundingDecision.ANSWER