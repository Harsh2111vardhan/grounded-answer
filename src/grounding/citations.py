from __future__ import annotations

import re
from dataclasses import dataclass


CITATION_RE = re.compile(
    r"§(?P<id>\d+\.\d+\.\d+(?:\([a-z]+\))?)"
)


@dataclass(frozen=True)
class CitationCheck:
    valid: bool
    citations: list[str]
    invalid_citations: list[str]


def extract_citations(text: str) -> list[str]:
    """Return unique clause citations in the order they appear."""
    seen: set[str] = set()
    citations: list[str] = []

    for match in CITATION_RE.finditer(text):
        clause_id = f"§{match.group('id')}"

        if clause_id not in seen:
            citations.append(clause_id)
            seen.add(clause_id)

    return citations


def validate_citations(
    answer: str,
    evidence_ids: set[str] | list[str],
) -> CitationCheck:
    """Check that every cited clause exists in the supplied evidence."""
    evidence_ids = set(evidence_ids)
    citations = extract_citations(answer)

    invalid = [
        citation
        for citation in citations
        if citation not in evidence_ids
    ]

    return CitationCheck(
        valid=not invalid,
        citations=citations,
        invalid_citations=invalid,
    )
