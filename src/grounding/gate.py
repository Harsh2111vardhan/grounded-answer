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
        question: str,
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
        # immediate grounding failure.
        if not citation_check.valid:
            return GroundingResult(
                decision=GroundingDecision.PARTIAL,
                answer=answer,
                citation_check=citation_check,
                entailments=[],
                conflicts=[],
                uncited_sentences=uncited_sentences,
            )

        # Check the retrieved evidence for contradictions that are relevant
        # to the user's question.
        conflicts = self.conflict_checker.check_all(
            question,
            evidence,
        )

        # A relevant policy conflict takes precedence over the generated
        # answer. The system must not silently choose one provision.
        if conflicts:
            return GroundingResult(
                decision=GroundingDecision.CONFLICT,
                answer=answer,
                citation_check=citation_check,
                entailments=[],
                conflicts=conflicts,
                uncited_sentences=uncited_sentences,
            )

        claims = extract_claims(answer)

        # An answer without verifiable claims cannot be safely grounded.
        if not claims:
            return GroundingResult(
                decision=GroundingDecision.REFUSE,
                answer=answer,
                citation_check=citation_check,
                entailments=[],
                conflicts=[],
                uncited_sentences=uncited_sentences,
            )

        # Verify generated claims against the retrieved policy evidence.
        entailments = self.entailment_checker.check_all(
            claims,
            evidence,
        )

        # If none of the claims are supported and there is no relevant
        # policy conflict, refuse rather than allowing an unsupported answer.
        if not any(result.supported for result in entailments):
            return GroundingResult(
                decision=GroundingDecision.REFUSE,
                answer=answer,
                citation_check=citation_check,
                entailments=entailments,
                conflicts=[],
                uncited_sentences=uncited_sentences,
            )

        if all(result.supported for result in entailments):
            decision = GroundingDecision.ANSWER
        else:
            decision = GroundingDecision.PARTIAL

        return GroundingResult(
            decision=decision,
            answer=answer,
            citation_check=citation_check,
            entailments=entailments,
            conflicts=[],
            uncited_sentences=uncited_sentences,
        )