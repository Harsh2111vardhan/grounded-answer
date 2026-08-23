from __future__ import annotations

import re
from dataclasses import dataclass


CITATION_RE = re.compile(
    r"§(?P<id>\d+\.\d+\.\d+(?:\([a-z]+\))?)"
)


@dataclass(frozen=True)
class Claim:
    text: str
    citation: str


def extract_claims(
    answer: str,
) -> list[Claim]:
    """
    Extract one claim for every citation.

    A citation belongs to the factual text immediately preceding it.
    Multiple citations in the same sentence create separate claims.
    """

    claims: list[Claim] = []

    for match in CITATION_RE.finditer(answer):
        citation = f"§{match.group('id')}"

        # Look backwards from the citation to the beginning of the
        # current sentence.
        before = answer[:match.start()]

        sentence_match = re.search(
            r"([^.!?\n]*(?:[.!?])?)\s*$",
            before,
        )

        claim_text = (
            sentence_match.group(1).strip()
            if sentence_match
            else before.strip()
        )

        claim_text = re.sub(
            r"^\s*[-*•]\s*",
            "",
            claim_text,
        ).strip()

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
        sentence = sentence.strip()

        if not sentence:
            continue

        sentence = re.sub(
            r"^\s*[-*•]\s*",
            "",
            sentence,
        ).strip()

        if not sentence:
            continue

        # Ignore headings and obvious non-substantive formatting.
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