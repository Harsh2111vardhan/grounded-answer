from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class PolicyClause:
    clause_id: str
    text: str
    part: str
    section: str
    line_no: int

    effective_from: date | None = None
    effective_to: date | None = None
    applicability_basis: str | None = None
    source: str = "policy-manual"


@dataclass
class Evidence:
    clause_id: str
    text: str
    part: str
    section: str
    line_no: int

    bm25_score: float | None = None
    semantic_score: float | None = None
    fused_rank: int | None = None

    retrieval_sources: list[str] = field(default_factory=list)
    cross_reference_of: str | None = None

    reference_consistent: bool | None = None
    reference_inconsistency_note: str | None = None

    effective_from: date | None = None
    effective_to: date | None = None
    applicability_basis: str | None = None
    source: str = "policy-manual"


DecisionOutcome = Literal["ANSWER", "CONFLICT", "REFUSE", "PARTIAL"]


@dataclass
class ConflictRecord:
    clause_ids: list[str]
    proposition_summary: str
    detection_method: Literal[
        "reference_inconsistency",
        "proposition_mismatch",
    ]


@dataclass
class Claim:
    text: str
    citations: list[str] = field(default_factory=list)


@dataclass
class SubAnswer:
    sub_question: str
    outcome: Literal["ANSWER", "REFUSE", "CONFLICT"]
    text: str
    citations: list[str] = field(default_factory=list)
    conflict: ConflictRecord | None = None
    escalation: str | None = None


@dataclass
class Decision:
    outcome: DecisionOutcome
    sub_answers: list[SubAnswer]
    evidence_used: list[str] = field(default_factory=list)
    evidence_considered: list[str] = field(default_factory=list)