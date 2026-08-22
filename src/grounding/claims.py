from __future__ import annotations

import re
from dataclasses import dataclass

from .citations import extract_citations


@dataclass(frozen=True)
class Claim:
    text: str
    citation: str


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def extract_claims(answer: str) -> list[Claim]:
    claims: list[Claim] = []

    for sentence in _split_sentences(answer):
        citations = extract_citations(sentence)
        if not citations:
            continue

        claim_text = re.sub(
            r"\s*§\d+\.\d+\.\d+(?:\([a-z]+\))?",
            "",
            sentence,
        ).strip()

        for citation in citations:
            claims.append(Claim(text=claim_text, citation=citation))

    return claims


def find_uncited_sentences(answer: str) -> list[str]:
    return [
        sentence
        for sentence in _split_sentences(answer)
        if not extract_citations(sentence)
    ]
