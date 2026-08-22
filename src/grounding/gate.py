from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..models import Evidence
from .citations import CitationCheck, validate_citations
from .claims import extract_claims, find_uncited_sentences
from .conflict import ConflictChecker, ConflictResult
from .entailment import EntailmentChecker, EntailmentResult


class GroundingDecision(str, Enum):
    ANSWER = "ANSWER"
    PARTIAL = "PARTIAL"
    REFUSE = "REFUSE"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class GroundingResult:
    decision: GroundingDecision
    answer: str
    citation_check: CitationCheck
    entailments: list[EntailmentResult]
    conflicts: list[ConflictResult]
    uncited_sentences: list[str]


class GroundingGate:
    def __init__(
        self,
        entailment_checker: EntailmentChecker,
        conflict_checker: ConflictChecker,
    ):
        self.entailment_checker = entailment_checker
        self.conflict_checker = conflict_checker

    def evaluate(
        self,
        answer: str,
        evidence: list[Evidence],
    ) -> GroundingResult:
        citation_check = validate_citations(
            answer,
            {item.clause_id for item in evidence},
        )

        uncited_sentences = find_uncited_sentences(answer)

        # No evidence means there is nothing safe to ground the answer in.
        if not evidence:
            return GroundingResult(
                decision=GroundingDecision.REFUSE,
                answer=answer,
                citation_check=citation_check,
                entailments=[],
                conflicts=[],
                uncited_sentences=uncited_sentences,
            )

        # A citation that does not exist in the retrieved evidence is an
        # immediate grounding failure. Don't spend more API calls verifying it.
        if not citation_check.valid:
            return GroundingResult(
                decision=GroundingDecision.PARTIAL,
                answer=answer,
                citation_check=citation_check,
                entailments=[],
                conflicts=[],
                uncited_sentences=uncited_sentences,
            )

        claims = extract_claims(answer)

        if not claims:
            return GroundingResult(
                decision=GroundingDecision.REFUSE,
                answer=answer,
                citation_check=citation_check,
                entailments=[],
                conflicts=[],
                uncited_sentences=uncited_sentences,
            )

        # Verify claims first.
        entailments = self.entailment_checker.check_all(
            claims,
            evidence,
        )

        # If no claims are supported, don't waste API calls looking for
        # conflicts in unrelated evidence.
        if not any(result.supported for result in entailments):
            return GroundingResult(
                decision=GroundingDecision.REFUSE,
                answer=answer,
                citation_check=citation_check,
                entailments=entailments,
                conflicts=[],
                uncited_sentences=uncited_sentences,
            )

        # Only run conflict detection after we know the answer has at least
        # some grounded content.
        conflicts = self.conflict_checker.check_all(evidence)

        if conflicts:
            decision = GroundingDecision.CONFLICT
        elif all(result.supported for result in entailments):
            decision = GroundingDecision.ANSWER
        else:
            decision = GroundingDecision.PARTIAL

        return GroundingResult(
            decision=decision,
            answer=answer,
            citation_check=citation_check,
            entailments=entailments,
            conflicts=conflicts,
            uncited_sentences=uncited_sentences,
        )


def format_grounding_result(result: GroundingResult) -> str:
    """Turn a grounding decision into a user-facing response."""

    if result.decision == GroundingDecision.CONFLICT:
        lines = [
            "The policy manual contains conflicting provisions relevant to this question."
        ]

        for conflict in result.conflicts:
            lines.append(
                f"{conflict.clause_a} and {conflict.clause_b}: "
                f"{conflict.reason}"
            )

        lines.append(
            "The supplied provisions do not establish which requirement "
            "takes precedence."
        )

        return "\n".join(lines)

    if result.decision == GroundingDecision.REFUSE:
        return (
            "I can't give a grounded answer from the policy evidence "
            "retrieved for this question."
        )

    if result.decision == GroundingDecision.PARTIAL:
        return (
            f"{result.answer}\n\n"
            "Some parts of this answer could not be fully supported "
            "by the retrieved policy evidence."
        )

    return result.answer