from __future__ import annotations

import re
from dataclasses import dataclass


CITATION_RE = re.compile(
    r"§\d+\.\d+\.\d+(?:\([a-z]+\))?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Claim:
    text: str
    citation: str


def _strip_list_marker(text: str) -> str:
    return re.sub(
        r"^\s*[-*•]\s*",
        "",
        text,
    ).strip()


def _extract_claim_text(
    answer: str,
    citation_start: int,
) -> str:
    """
    Extract the factual sentence immediately preceding a citation.

    The citation itself is not included in the claim.
    """

    prefix = answer[:citation_start].rstrip()

    if not prefix:
        return ""

    # Split only on actual sentence boundaries.
    parts = re.split(
        r"(?<=[.!?])\s+|\n+",
        prefix,
    )

    claim = parts[-1].strip()

    if not claim and len(parts) > 1:
        claim = parts[-2].strip()

    return _strip_list_marker(claim)


def extract_claims(
    answer: str,
) -> list[Claim]:
    """
    Create one Claim for every policy citation.

    Example:

        The rule is described in §4.3.2 and confirmed by §9.1.4.

    produces two claims, one for each citation.

    A citation at the end of a sentence belongs to the complete sentence
    immediately preceding it.
    """

    claims: list[Claim] = []

    matches = list(
        CITATION_RE.finditer(answer)
    )

    for match in matches:
        citation = match.group(0)

        claim_text = _extract_claim_text(
            answer,
            match.start(),
        )

        if not claim_text:
            continue

        claims.append(
            Claim(
                text=claim_text,
                citation=citation,
            )
        )

    return claims


def find_uncited_sentences(
    answer: str,
) -> list[str]:
    """
    Return substantive sentences that do not contain a policy citation.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+|\n+",
        answer.strip(),
    )

    uncited: list[str] = []

    for sentence in sentences:
        sentence = _strip_list_marker(
            sentence.strip()
        )

        if not sentence:
            continue

        if sentence.upper() in {
            "SOURCES",
            "PARTIAL ANSWER",
            "ANSWER",
            "REFUSAL",
            "CONFLICT",
        }:
            continue

        if not CITATION_RE.search(sentence):
            uncited.append(sentence)

    return uncited