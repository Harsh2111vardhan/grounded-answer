from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..models import PolicyClause
from .temporal import select_date


@dataclass(frozen=True)
class ApplicabilityRule:
    operation_group: int
    basis: str
    effective_date: date


@dataclass(frozen=True)
class AmendmentChange:
    amendment_id: str
    source_path: str
    paragraph: str
    target_clause_id: str | None
    operation: str
    old_text: str | None
    new_text: str | None
    table_text: str | None
    inserted_clause_id: str | None
    inserted_text: str | None
    applicability_basis: str
    effective_date: date


@dataclass(frozen=True)
class Amendment:
    amendment_id: str
    issued: date | None
    effective: date
    source_path: str
    changes: tuple[AmendmentChange, ...]


DATE_RE = re.compile(
    r"\b"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>"
    r"January|February|March|April|May|June|July|August|"
    r"September|October|November|December"
    r")\s+"
    r"(?P<year>\d{4})"
    r"\b",
    re.IGNORECASE,
)

AMENDMENT_ID_RE = re.compile(
    r"Amendment\s+No\.\s*([A-Za-z0-9._-]+)",
    re.IGNORECASE,
)

HEADER_RE = re.compile(
    r"^\s*\*\*(Issued|Effective):\*\*\s*(.+?)\s*$",
    re.IGNORECASE,
)

PARAGRAPH_RE = re.compile(
    r"^\s*\*\*(\d+\.\d+)\*\*\s*(.*)$"
)

SECTION_RE = re.compile(
    r"^\s*##\s+(\d+)\.\s+(.+?)\s*$"
)

CLAUSE_RE = re.compile(
    r"\b§(?P<id>\d+\.\d+\.\d+(?:\([a-z]+\)|[A-Za-z]+)?)",
    re.IGNORECASE,
)

INSERTED_CLAUSE_RE = re.compile(
    r"\*\*(?P<id>\d+\.\d+\.\d+(?:[A-Za-z]+)?)\*\*\s*"
    r"(?P<text>.+)",
    re.IGNORECASE,
)


def _parse_date(text: str) -> date:
    match = DATE_RE.search(text)

    if not match:
        raise ValueError(
            f"Could not parse date from amendment text: {text!r}"
        )

    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    return date(
        int(match.group("year")),
        months[match.group("month").lower()],
        int(match.group("day")),
    )


def _clean(value: str) -> str:
    value = value.strip()

    value = value.replace('**"', '**')
    value = value.replace('"**', '**')
    value = value.replace("'**", "**")
    value = value.replace("**'", "**")

    value = re.sub(
        r"^\*\*(.*?)\*\*$",
        r"\1",
        value,
    )

    return value.strip(
        "\"'"
    ).strip()


def _extract_header_dates(
    lines: list[str],
) -> tuple[date | None, date]:
    issued: date | None = None
    effective: date | None = None

    for line in lines:
        match = HEADER_RE.match(line)

        if not match:
            continue

        label = match.group(1).lower()
        parsed = _parse_date(match.group(2))

        if label == "issued":
            issued = parsed
        elif label == "effective":
            effective = parsed

    if effective is None:
        raise ValueError(
            "Amendment does not contain an Effective date."
        )

    return issued, effective


def _extract_paragraph_blocks(
    lines: list[str],
) -> list[tuple[str, str]]:
    """
    Extract actual amendment paragraphs such as 1.1, 2.1, 2.2, etc.

    Markdown section headings (## 2. Reporting...) are not amendment
    operations and therefore terminate the previous paragraph rather than
    becoming part of its text.
    """

    blocks: list[tuple[str, str]] = []

    current_id: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_id, current_lines

        if current_id is not None:
            text = "\n".join(
                current_lines
            ).strip()

            if text:
                blocks.append(
                    (
                        current_id,
                        text,
                    )
                )

        current_id = None
        current_lines = []

    for line in lines:
        paragraph_match = PARAGRAPH_RE.match(
            line
        )

        if paragraph_match:
            flush()

            current_id = paragraph_match.group(
                1
            )

            current_lines = [
                paragraph_match.group(2).strip()
            ]

            continue

        section_match = SECTION_RE.match(
            line
        )

        if section_match:
            flush()
            continue

        if current_id is not None:
            current_lines.append(line)

    flush()

    return blocks


def _operation_group(
    paragraph: str,
) -> int:
    return int(
        paragraph.split(
            ".",
            1,
        )[0]
    )


def _extract_applicability(
    lines: list[str],
    default_effective: date,
) -> dict[int, ApplicabilityRule]:
    """
    Read transitional paragraph 5 from the amendment itself.

    Paragraph 5.1:
      paragraphs 1, 3 and 4 -> determination date

    Paragraph 5.2:
      paragraph 2 -> event date

    Paragraph 5.3 is a spanning-period rule and does not change the
    applicability basis of the six amendment operations.
    """

    rules: dict[int, ApplicabilityRule] = {}

    text = "\n".join(lines)

    paragraph_51 = re.search(
        r"\*\*5\.1\*\*(.*?)(?=\n\s*\*\*5\.2\*\*|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if paragraph_51:
        content = paragraph_51.group(1)

        for group in (1, 3, 4):
            rules[group] = ApplicabilityRule(
                operation_group=group,
                basis="determination",
                effective_date=default_effective,
            )

    paragraph_52 = re.search(
        r"\*\*5\.2\*\*(.*?)(?=\n\s*\*\*5\.3\*\*|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if paragraph_52:
        rules[2] = ApplicabilityRule(
            operation_group=2,
            basis="event",
            effective_date=default_effective,
        )

    return rules


def _parse_substitution(
    paragraph: str,
    amendment_id: str,
    source_path: str,
    effective: date,
    rule: ApplicabilityRule,
) -> AmendmentChange | None:
    match = re.search(
        r"In\s+§(?P<target>\d+\.\d+\.\d+"
        r"(?:\([a-z]+\)|[A-Za-z]+)?)"
        r"\s*,?\s*"
        r"for\s+"
        r"(?P<quote>['\"])(?P<old>.+?)(?P=quote)"
        r".*?"
        r"substitute\s+"
        r"(?P<new>.+?)(?:\.|$)",
        paragraph,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    new_text = _clean(
        match.group("new")
    )

    return AmendmentChange(
        amendment_id=amendment_id,
        source_path=source_path,
        paragraph=paragraph_id_from_text(paragraph),
        target_clause_id=(
            f"§{match.group('target')}"
        ),
        operation="substitute",
        old_text=_clean(
            match.group("old")
        ),
        new_text=new_text,
        table_text=None,
        inserted_clause_id=None,
        inserted_text=None,
        applicability_basis=rule.basis,
        effective_date=rule.effective_date,
    )


def paragraph_id_from_text(
    text: str,
) -> str:
    match = re.search(
        r"^\s*\*\*(\d+\.\d+)\*\*",
        text,
    )

    if match:
        return match.group(1)

    return ""


def _parse_table_change(
    paragraph_id: str,
    paragraph: str,
    amendment_id: str,
    source_path: str,
    rule: ApplicabilityRule,
) -> AmendmentChange | None:
    match = re.search(
        r"In\s+the\s+table\s+at\s+§(?P<target>\d+\.\d+\.\d+"
        r"(?:\([a-z]+\)|[A-Za-z]+)?)"
        r".*?substitute\s+the\s+following\s+—?"
        r"(?P<table>.*)",
        paragraph,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    table_lines = []

    for line in match.group("table").splitlines():
        line = line.strip()

        if not line.startswith("|"):
            continue

        if re.fullmatch(
            r"\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?",
            line,
        ):
            continue

        table_lines.append(line)

    if not table_lines:
        return None

    return AmendmentChange(
        amendment_id=amendment_id,
        source_path=source_path,
        paragraph=paragraph_id,
        target_clause_id=(
            f"§{match.group('target')}"
        ),
        operation="replace_table",
        old_text=None,
        new_text=None,
        table_text="\n".join(table_lines),
        inserted_clause_id=None,
        inserted_text=None,
        applicability_basis=rule.basis,
        effective_date=rule.effective_date,
    )


def _parse_insert(
    paragraph_id: str,
    paragraph: str,
    amendment_id: str,
    source_path: str,
    rule: ApplicabilityRule,
) -> AmendmentChange | None:
    target_match = re.search(
        r"After\s+§(?P<target>\d+\.\d+\.\d+"
        r"(?:\([a-z]+\)|[A-Za-z]+)?)"
        r".*?insert",
        paragraph,
        re.IGNORECASE | re.DOTALL,
    )

    if not target_match:
        return None

    inserted_match = re.search(
        r">\s*\*\*(?P<id>\d+\.\d+\.\d+[A-Za-z]?)\*\*\s*"
        r"(?P<text>.+)",
        paragraph,
        re.IGNORECASE | re.DOTALL,
    )

    if not inserted_match:
        inserted_match = re.search(
            r"\*\*(?P<id>\d+\.\d+\.\d+[A-Za-z]?)\*\*\s*"
            r"(?P<text>.+)",
            paragraph,
            re.IGNORECASE | re.DOTALL,
        )

    if not inserted_match:
        return None

    return AmendmentChange(
        amendment_id=amendment_id,
        source_path=source_path,
        paragraph=paragraph_id,
        target_clause_id=(
            f"§{target_match.group('target')}"
        ),
        operation="insert",
        old_text=None,
        new_text=None,
        table_text=None,
        inserted_clause_id=(
            f"§{inserted_match.group('id')}"
        ),
        inserted_text=_clean(
            inserted_match.group("text")
        ),
        applicability_basis=rule.basis,
        effective_date=rule.effective_date,
    )


def _parse_change(
    paragraph_id: str,
    paragraph: str,
    amendment_id: str,
    source_path: str,
    effective: date,
    rules: dict[int, ApplicabilityRule],
) -> AmendmentChange | None:
    group = _operation_group(
        paragraph_id
    )

    rule = rules.get(
        group,
        ApplicabilityRule(
            operation_group=group,
            basis="determination",
            effective_date=effective,
        ),
    )

    table_change = _parse_table_change(
        paragraph_id,
        paragraph,
        amendment_id,
        source_path,
        rule,
    )

    if table_change:
        return table_change

    insert_change = _parse_insert(
        paragraph_id,
        paragraph,
        amendment_id,
        source_path,
        rule,
    )

    if insert_change:
        return insert_change

    substitution = re.search(
        r"In\s+§(?P<target>\d+\.\d+\.\d+"
        r"(?:\([a-z]+\)|[A-Za-z]+)?)"
        r"\s*,?\s*"
        r"for\s+"
        r"(?P<quote>['\"])(?P<old>.+?)(?P=quote)"
        r"\s*\(?"
        r"(?P<suffix>\s*"
        r"\(in\s+both\s+places\s+where\s+it\s+occurs\))?"
        r".*?"
        r"substitute\s+"
        r"(?P<new>.+?)(?:\.|$)",
        paragraph,
        re.IGNORECASE | re.DOTALL,
    )

    if substitution:
        return AmendmentChange(
            amendment_id=amendment_id,
            source_path=source_path,
            paragraph=paragraph_id,
            target_clause_id=(
                f"§{substitution.group('target')}"
            ),
            operation="substitute",
            old_text=_clean(
                substitution.group("old")
            ),
            new_text=_clean(
                substitution.group("new")
            ),
            table_text=None,
            inserted_clause_id=None,
            inserted_text=None,
            applicability_basis=rule.basis,
            effective_date=rule.effective_date,
        )

    return None


def parse_amendment(
    path: str | Path,
) -> Amendment:
    path = Path(path)

    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()

    issued, effective = _extract_header_dates(
        lines
    )

    amendment_match = AMENDMENT_ID_RE.search(
        "\n".join(lines)
    )

    amendment_id = (
        amendment_match.group(1)
        if amendment_match
        else path.stem
    )

    rules = _extract_applicability(
        lines,
        effective,
    )

    changes: list[AmendmentChange] = []

    for paragraph_id, paragraph in _extract_paragraph_blocks(
        lines
    ):
        change = _parse_change(
            paragraph_id=paragraph_id,
            paragraph=paragraph,
            amendment_id=amendment_id,
            source_path=str(path),
            effective=effective,
            rules=rules,
        )

        if change:
            changes.append(change)

    return Amendment(
        amendment_id=amendment_id,
        issued=issued,
        effective=effective,
        source_path=str(path),
        changes=tuple(changes),
    )


def _apply_change(
    clause: PolicyClause,
    change: AmendmentChange,
) -> PolicyClause:
    if change.operation == "substitute":
        old = change.old_text or ""
        new = change.new_text or ""

        if old not in clause.text:
            raise ValueError(
                f"Amendment target text not found in "
                f"{clause.clause_id}: {old!r}"
            )

        text = clause.text.replace(
            old,
            new,
        )

    elif change.operation == "replace_table":
        marker = "\n\nTable:\n"

        if marker in clause.text:
            prefix = clause.text.split(
                marker,
                1,
            )[0]
        else:
            prefix = clause.text

        text = (
            f"{prefix}"
            f"{marker}"
            f"{change.table_text or ''}"
        )

    else:
        text = clause.text

    return PolicyClause(
        clause_id=clause.clause_id,
        text=text,
        part=clause.part,
        section=clause.section,
        line_no=clause.line_no,
    )


def apply_amendments(
    base_clauses: list[PolicyClause],
    amendments: list[Amendment],
    event_date: date | None = None,
    determination_date: date | None = None,
) -> list[PolicyClause]:
    clauses = list(
        base_clauses
    )

    amendments = sorted(
        amendments,
        key=lambda item: item.effective,
    )

    for amendment in amendments:
        for change in amendment.changes:

            if change.applicability_basis == "event":
                selected = event_date

            elif change.applicability_basis == "determination":
                selected = determination_date

            else:
                selected = (
                    event_date
                    or determination_date
                )

            if selected is None:
                continue

            if selected < change.effective_date:
                continue

            if change.operation in {
                "substitute",
                "replace_table",
            }:
                for index, clause in enumerate(
                    clauses
                ):
                    if (
                        clause.clause_id
                        == change.target_clause_id
                    ):
                        clauses[index] = _apply_change(
                            clause,
                            change,
                        )
                        break

            elif (
                change.operation == "insert"
                and change.inserted_clause_id
            ):
                if any(
                    clause.clause_id
                    == change.inserted_clause_id
                    for clause in clauses
                ):
                    continue

                target_index = next(
                    (
                        index
                        for index, clause
                        in enumerate(clauses)
                        if clause.clause_id
                        == change.target_clause_id
                    ),
                    None,
                )

                if target_index is None:
                    continue

                target = clauses[
                    target_index
                ]

                inserted = PolicyClause(
                    clause_id=(
                        change.inserted_clause_id
                    ),
                    text=(
                        change.inserted_text
                        or ""
                    ),
                    part=target.part,
                    section=target.section,
                    line_no=0,
                )

                clauses.insert(
                    target_index + 1,
                    inserted,
                )

    return clauses