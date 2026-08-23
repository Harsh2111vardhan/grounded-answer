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
    """
    Extract only numbers that are part of explicit time periods.

    This prevents section numbers such as §9.1.4 from being interpreted
    as deadline values.
    """
    matches = re.findall(
        r"\b(\d+)\s+(?:calendar\s+)?"
        r"(?:day|days|week|weeks|month|months|year|years)\b",
        text.lower(),
    )

    return [int(value) for value in matches]


def _has_deadline(text: str) -> bool:
    return bool(
        re.search(
            r"\b\d+\s+(?:calendar\s+)?"
            r"(?:day|days|week|weeks|month|months|year|years)\b",
            text.lower(),
        )
    )


def _potential_conflict_pair(
    clause_a: Evidence,
    clause_b: Evidence,
) -> bool:
    """
    Cheap filter before checking a pair for an actual conflict.
    """
    overlap = _terms(clause_a.text) & _terms(clause_b.text)

    return len(overlap) >= 2


def _question_relevant(
    question: str,
    clause_a: Evidence,
    clause_b: Evidence,
) -> bool:
    """
    Only consider a conflict when both clauses share meaningful
    subject matter with the user's question.
    """
    question_terms = _terms(question)

    if not question_terms:
        return False

    shared_clause_terms = (
        _terms(clause_a.text)
        & _terms(clause_b.text)
    )

    relevant_terms = question_terms & shared_clause_terms

    return len(relevant_terms) >= 2


def _deadline_conflict(
    clause_a: Evidence,
    clause_b: Evidence,
) -> str | None:
    """
    Detect clear deadline contradictions.

    Different time periods are not automatically contradictory.
    The clauses must describe the same type of obligation.

    For example:
        §4.3.2 -> report a change within 10 days
        §9.1.4 -> reported change within 30 days

    is a potential conflict.

    But:
        §9.6.1 -> exclusion for 13 weeks
        §9.1.4 -> reporting within 30 days

    is not a deadline conflict because exclusion and reporting are
    different obligations.
    """
    if not (_has_deadline(clause_a.text) and _has_deadline(clause_b.text)):
        return None

    numbers_a = _numbers(clause_a.text)
    numbers_b = _numbers(clause_b.text)

    if not numbers_a or not numbers_b:
        return None

    if numbers_a[0] == numbers_b[0]:
        return None

    terms_a = _terms(clause_a.text)
    terms_b = _terms(clause_b.text)

    shared = terms_a & terms_b

    # Reporting / notification obligation.
    reporting_terms = {
        "report",
        "reported",
        "reporting",
        "notify",
        "notification",
        "notice",
    }

    if shared & reporting_terms:
        return (
            f"The clauses contain different deadlines "
            f"({numbers_a[0]} vs {numbers_b[0]})."
        )

    # Application / submission obligation.
    application_terms = {
        "application",
        "applicant",
        "submit",
        "submitted",
        "submission",
    }

    if len(shared & application_terms) >= 2:
        return (
            f"The clauses contain different deadlines "
            f"({numbers_a[0]} vs {numbers_b[0]})."
        )

    # Interview / attendance obligation.
    interview_terms = {
        "interview",
        "attend",
        "attendance",
    }

    if len(shared & interview_terms) >= 1:
        return (
            f"The clauses contain different deadlines "
            f"({numbers_a[0]} vs {numbers_b[0]})."
        )

    # Review / appeal obligation.
    review_terms = {
        "review",
        "appeal",
        "exercise",
    }

    if len(shared & review_terms) >= 1:
        return (
            f"The clauses contain different deadlines "
            f"({numbers_a[0]} vs {numbers_b[0]})."
        )

    return None


class ConflictChecker:
    """
    Local conflict detector.

    The checker does not call an LLM. It detects clear textual
    contradictions while avoiding unrelated time periods being treated
    as conflicting rules.
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

        reason = _deadline_conflict(
            clause_a,
            clause_b,
        )

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
        question: str,
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

                if not _question_relevant(
                    question,
                    clause_a,
                    clause_b,
                ):
                    continue

                result = self.check(
                    clause_a,
                    clause_b,
                )

                if result.conflict:
                    results.append(result)

        return results