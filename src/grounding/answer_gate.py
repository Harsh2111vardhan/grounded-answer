from __future__ import annotations

from dataclasses import dataclass

from ..models import Evidence
from .citations import CitationCheck, validate_citations


@dataclass(frozen=True)
class CitationGateResult:
    passed: bool
    answer: str
    citation_check: CitationCheck


def check_answer_citations(
    answer: str,
    evidence: list[Evidence],
) -> CitationGateResult:
    """Run the mechanical citation-integrity check."""
    evidence_ids = {item.clause_id for item in evidence}

    citation_check = validate_citations(
        answer,
        evidence_ids,
    )

    return CitationGateResult(
        passed=citation_check.valid,
        answer=answer,
        citation_check=citation_check,
    )
