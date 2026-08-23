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
    overlap = _terms(clause_a.text) & _terms(clause_b.text)
    return len(overlap) >= 2


def _is_method_question(question: str) -> bool:
    """
    Detect questions asking how/where/by what means an action can be
    performed rather than asking about the deadline for that action.
    """

    normalized = question.lower()

    method_patterns = (
        r"\bhow\s+(?:can|do|does|may|should|must)\b",
        r"\bhow\s+to\b",
        r"\bwhat\s+(?:way|ways|method|methods)\b",
        r"\bwhere\s+(?:can|do|does|may|should)\b",
        r"\bby\s+what\s+(?:method|means)\b",
        r"\bwhat\s+are\s+the\s+(?:ways|methods)\b",
    )

    return any(
        re.search(pattern, normalized)
        for pattern in method_patterns
    )


def _is_deadline_question(question: str) -> bool:
    """
    Detect questions where the requested policy attribute is a deadline,
    reporting period, time limit, or similar time requirement.
    """

    normalized = question.lower()

    deadline_terms = (
        r"\bdeadline\b",
        r"\bhow\s+long\b",
        r"\bhow\s+many\s+days\b",
        r"\bhow\s+many\s+weeks\b",
        r"\bhow\s+many\s+months\b",
        r"\btime\s+limit\b",
        r"\btime\s+period\b",
        r"\bwithin\s+what\b",
        r"\bwhen\s+must\b",
        r"\bwhen\s+should\b",
        r"\bby\s+when\b",
    )

    return any(
        re.search(pattern, normalized)
        for pattern in deadline_terms
    )


def _question_relevant(
    question: str,
    clause_a: Evidence,
    clause_b: Evidence,
) -> bool:
    """
    Determine whether a conflict between two clauses is relevant to the
    specific aspect of policy asked about.

    Generic lexical overlap is retained for ordinary questions, but a
    deadline conflict is not treated as relevant to a question asking only
    how or where an action is performed.
    """

    question_terms = _terms(question)

    if not question_terms:
        return False

    shared_clause_terms = (
        _terms(clause_a.text)
        & _terms(clause_b.text)
    )

    relevant_terms = question_terms & shared_clause_terms

    if len(relevant_terms) < 2:
        return False

    # A conflict between reporting deadlines should only block an answer
    # when the question is actually asking about the deadline/time limit.
    if (
        _has_deadline(clause_a.text)
        and _has_deadline(clause_b.text)
        and _is_method_question(question)
        and not _is_deadline_question(question)
    ):
        return False

    return True


def _deadline_conflict(
    clause_a: Evidence,
    clause_b: Evidence,
) -> str | None:
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

    Detects clear textual contradictions while considering whether the
    contradiction is relevant to the specific question being asked.
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