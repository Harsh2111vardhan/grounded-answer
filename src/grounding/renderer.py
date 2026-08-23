from __future__ import annotations

import re

from ..models import Evidence
from .gate import GroundingDecision, GroundingResult


_CITATION_PATTERN = re.compile(r"§\d+(?:\.\d+)+")


def _citation_for_text(text: str) -> str:
    """Convert inline clause citations into visually distinct citations."""
    return _CITATION_PATTERN.sub(
        lambda match: f"【{match.group(0)}】",
        text,
    )


def _grounding_check_block(
    result: GroundingResult,
) -> list[str]:
    """
    Render the evidence-based grounding decision.

    The grounding check exposes the checks already performed by
    GroundingGate. It does not introduce a separate confidence score.
    """

    if result.decision == GroundingDecision.ANSWER:
        evidence_status = "sufficient"
        claim_status = (
            "supported"
            if any(item.supported for item in result.entailments)
            else "unsupported"
        )
        conflict_status = "none"

    elif result.decision == GroundingDecision.PARTIAL:
        evidence_status = "partial"
        claim_status = (
            "partially supported"
            if any(item.supported for item in result.entailments)
            else "unsupported"
        )
        conflict_status = "none"

    elif result.decision == GroundingDecision.CONFLICT:
        evidence_status = "sufficient"
        claim_status = "not evaluated"
        conflict_status = "detected"

    else:
        evidence_status = (
            "insufficient"
            if not result.entailments
            or not any(item.supported for item in result.entailments)
            else "partial"
        )

        claim_status = (
            "unsupported"
            if not any(item.supported for item in result.entailments)
            else "partially supported"
        )

        conflict_status = (
            "detected"
            if result.conflicts
            else "none"
        )

    # Use the production CitationCheck when available, while remaining
    # compatible with lightweight test stubs.
    citation_valid = getattr(
        result.citation_check,
        "valid",
        not bool(
            getattr(
                result.citation_check,
                "invalid_citations",
                [],
            )
        ),
    )

    citation_status = "valid" if citation_valid else "invalid"

    return [
        "",
        "GROUNDING CHECK",
        "────────────────────────────────────────",
        f"Evidence:      {evidence_status}",
        f"Citation:      {citation_status}",
        f"Conflict:      {conflict_status}",
        f"Claim support: {claim_status}",
        f"Decision:      {result.decision.value}",
    ]


def _source_block(
    clause_ids: list[str],
    evidence: list[Evidence],
) -> list[str]:
    evidence_by_id = {
        item.clause_id: item
        for item in evidence
    }

    lines = [
        "",
        "SOURCES",
        "────────────────────────────────────────",
    ]

    for clause_id in clause_ids:
        item = evidence_by_id.get(clause_id)

        if item is None:
            continue

        lines.append(clause_id)
        lines.append(item.text)
        lines.append("")

    return lines


def render_grounding_result(
    result: GroundingResult,
    evidence: list[Evidence],
) -> str:
    """Render a grounding result as readable CLI output."""

    if result.decision == GroundingDecision.ANSWER:
        answer = _citation_for_text(result.answer)

        citation_ids = list(
            dict.fromkeys(result.citation_check.citations)
        )

        lines = [
            "ANSWER",
            "────────────────────────────────────────",
            "",
            answer,
        ]

        lines.extend(
            _grounding_check_block(result)
        )

        lines.extend(
            _source_block(
                citation_ids,
                evidence,
            )
        )

        return "\n".join(lines).rstrip()

    if result.decision == GroundingDecision.PARTIAL:
        answer = _citation_for_text(result.answer)

        citation_ids = list(
            dict.fromkeys(result.citation_check.citations)
        )

        lines = [
            "PARTIAL ANSWER",
            "────────────────────────────────────────",
            "",
            answer,
            "",
            "Some parts of this answer could not be fully supported "
            "by the retrieved policy evidence.",
        ]

        lines.extend(
            _grounding_check_block(result)
        )

        lines.extend(
            _source_block(
                citation_ids,
                evidence,
            )
        )

        return "\n".join(lines).rstrip()

    if result.decision == GroundingDecision.CONFLICT:
        lines = [
            "CONFLICT",
            "────────────────────────────────────────",
            "",
            "The manual contains conflicting provisions relevant "
            "to this question.",
            "",
        ]

        for conflict in result.conflicts:
            lines.append(f"{conflict.clause_a} says:")
            lines.append(
                _get_clause_text(
                    conflict.clause_a,
                    evidence,
                )
            )
            lines.append("")

            lines.append(f"{conflict.clause_b} says:")
            lines.append(
                _get_clause_text(
                    conflict.clause_b,
                    evidence,
                )
            )
            lines.append("")

            lines.append(f"Conflict: {conflict.reason}")
            lines.append("")

        lines.append(
            "The manual does not establish which requirement "
            "takes precedence."
        )

        lines.extend(
            _grounding_check_block(result)
        )

        lines.extend(
            _escalation_block()
        )

        return "\n".join(lines).rstrip()

    # REFUSE

    lines = [
        "REFUSAL",
        "────────────────────────────────────────",
        "",
        "The supplied policy evidence does not establish the answer.",
        "",
        "The retrieved provisions do not establish the specific "
        "information requested.",
    ]

    lines.extend(
        _grounding_check_block(result)
    )

    lines.extend(
        _escalation_block()
    )

    return "\n".join(lines).rstrip()


def _get_clause_text(
    clause_id: str,
    evidence: list[Evidence],
) -> str:
    for item in evidence:
        if item.clause_id == clause_id:
            return item.text

    return "Clause text was not available in the retrieved evidence."


def _escalation_block() -> list[str]:
    return [
        "",
        "NEXT STEP",
        "────────────────────────────────────────",
        "",
        "Please contact your local Department district office "
        "for clarification.",
    ]