from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Evidence


@dataclass(frozen=True)
class ConflictResult:
    clause_a: str
    clause_b: str
    conflict: bool
    reason: str


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "under",
    "with",
    "within",
    "must",
    "shall",
    "may",
    "will",
    "where",
}


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return {word for word in words if word not in STOPWORDS}


def _numbers(text: str) -> list[int]:
    return [
        int(value)
        for value in re.findall(r"\b\d+\b", text)
    ]


def _has_deadline(text: str) -> bool:
    return bool(
        re.search(
            r"\b\d+\s+(?:calendar\s+)?"
            r"(?:day|days|week|weeks|month|months|year|years)\b",
            text.lower(),
        )
    )


def _deadline_conflict(
    clause_a: Evidence,
    clause_b: Evidence,
) -> str | None:
    """
    Detect obvious deadline contradictions without using an LLM.

    This intentionally only flags cases where:
    - both clauses contain a deadline,
    - their subject matter overlaps,
    - and the numeric deadlines differ.
    """
    if not (_has_deadline(clause_a.text) and _has_deadline(clause_b.text)):
        return None

    overlap = _terms(clause_a.text) & _terms(clause_b.text)

    if len(overlap) < 2:
        return None

    numbers_a = _numbers(clause_a.text)
    numbers_b = _numbers(clause_b.text)

    if not numbers_a or not numbers_b:
        return None

    if numbers_a[0] == numbers_b[0]:
        return None

    return (
        f"The clauses contain different deadlines "
        f"({numbers_a[0]} vs {numbers_b[0]})."
    )


def _potential_conflict_pair(
    clause_a: Evidence,
    clause_b: Evidence,
) -> bool:
    """
    Cheap relevance filter.

    Only compare clauses that share meaningful terms.
    """
    overlap = _terms(clause_a.text) & _terms(clause_b.text)

    if len(overlap) >= 2:
        return True

    return False


class ConflictChecker:
    """
    Local conflict detector.

    This deliberately does not call an LLM. It catches clear contradictions
    that can be established from the text itself and avoids spending API
    quota on pairwise clause comparisons.
    """

    def check(
        self,
        clause_a: Evidence,
        clause_b: Evidence,
    ) -> ConflictResult:
        if clause_a.clause_id == clause_b.clause_id:
            return ConflictResult(
                clause_a=clause_a.clause_id,
                clause_b=clause_b.clause_id,
                conflict=False,
                reason="The same clause cannot conflict with itself.",
            )

        reason = _deadline_conflict(clause_a, clause_b)

        if reason:
            return ConflictResult(
                clause_a=clause_a.clause_id,
                clause_b=clause_b.clause_id,
                conflict=True,
                reason=reason,
            )

        return ConflictResult(
            clause_a=clause_a.clause_id,
            clause_b=clause_b.clause_id,
            conflict=False,
            reason="No clear textual conflict detected.",
        )

    def check_all(
        self,
        evidence: list[Evidence],
    ) -> list[ConflictResult]:
        results: list[ConflictResult] = []

        for index, clause_a in enumerate(evidence):
            for clause_b in evidence[index + 1:]:
                if not _potential_conflict_pair(
                    clause_a,
                    clause_b,
                ):
                    continue

                result = self.check(clause_a, clause_b)

                if result.conflict:
                    results.append(result)

        return results