from __future__ import annotations

import re
from pathlib import Path

from .models import PolicyClause


CLAUSE_RE = re.compile(
    r"^\s*\*\*"
    r"(?P<id>\d+\.\d+\.\d+(?:\([a-z]+\)|[A-Za-z]+)?)"
    r"(?:\s+(?P<title>[^*]+?))?"
    r"\*\*\s*(?P<text>.*)$"
)

POSSIBLE_CLAUSE_RE = re.compile(
    r"^\s*\*\*(?P<id>\d+\.\d+\.\d+(?:\([a-z]+\)|[A-Za-z]+)?)"
)

PART_RE = re.compile(
    r"^\s*#\s+Part\s+(?P<number>\d+)\s*[—-]\s*(?P<title>.+?)\s*$"
)

SECTION_RE = re.compile(
    r"^\s*##\s+(?P<section>\d+\.\d+)\s+(?P<title>.+?)\s*$"
)

TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")


def _table_line(line: str) -> bool:
    return bool(TABLE_ROW_RE.match(line))


def _is_table_separator(line: str) -> bool:
    if not _table_line(line):
        return False

    cells = [
        cell.strip()
        for cell in line.strip().strip("|").split("|")
    ]

    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell)
        for cell in cells
    )


def _format_table(lines: list[str]) -> str:
    rows = []

    for line in lines:
        if _is_table_separator(line):
            continue

        cells = [
            cell.strip()
            for cell in line.strip().strip("|").split("|")
        ]

        rows.append(" | ".join(cells))

    return "\n".join(rows)


def parse_policy(path: str | Path) -> list[PolicyClause]:
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()

    clauses = []

    current_id = None
    current_text = []
    current_part = ""
    current_section = ""
    current_line = 0
    pending_table = []

    def flush():
        nonlocal current_id, current_text, pending_table

        if current_id is None:
            return

        text = "\n".join(current_text).strip()

        if pending_table:
            table = _format_table(pending_table)

            if table:
                text = f"{text}\n\nTable:\n{table}".strip()

        clauses.append(
            PolicyClause(
                clause_id=f"§{current_id}",
                text=text,
                part=current_part,
                section=current_section,
                line_no=current_line,
            )
        )

        current_id = None
        current_text = []
        pending_table = []

    i = 0

    while i < len(lines):
        line = lines[i]

        part_match = PART_RE.match(line)

        if part_match:
            current_part = (
                f"Part {part_match.group('number')} — "
                f"{part_match.group('title').strip()}"
            )
            i += 1
            continue

        section_match = SECTION_RE.match(line)

        if section_match:
            current_section = section_match.group("section")
            i += 1
            continue

        clause_match = CLAUSE_RE.match(line)

        if clause_match:
            flush()

            current_id = clause_match.group("id")

            title = (clause_match.group("title") or "").strip()
            text = clause_match.group("text").strip()

            if title:
                text = f"{title} {text}".strip()

            current_text = [text]
            current_line = i + 1

            i += 1
            continue

        if current_id is not None:

            if _table_line(line):
                table_lines = []

                while i < len(lines) and _table_line(lines[i]):
                    table_lines.append(lines[i])
                    i += 1

                pending_table = table_lines
                continue

            stripped = line.strip()

            if stripped:
                current_text.append(stripped)

        i += 1

    flush()

    return clauses


def audit_policy(path: str | Path) -> dict:
    """
    Check the entire manual for clause-heading problems.

    This compares clause-like headings found directly in the source
    with clauses produced by the parser.
    """

    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()

    source_ids = []
    malformed_headings = []

    for line_number, line in enumerate(lines, start=1):

        possible = POSSIBLE_CLAUSE_RE.match(line)

        if possible:
            clause_id = f"§{possible.group('id')}"
            source_ids.append((clause_id, line_number))

            if not CLAUSE_RE.match(line):
                malformed_headings.append(
                    {
                        "line": line_number,
                        "text": line,
                        "clause_id": clause_id,
                    }
                )

    clauses = parse_policy(path)
    parsed_ids = [clause.clause_id for clause in clauses]

    source_id_values = [clause_id for clause_id, _ in source_ids]

    missing = [
        item
        for item in source_ids
        if item[0] not in parsed_ids
    ]

    duplicates = [
        clause_id
        for clause_id in set(parsed_ids)
        if parsed_ids.count(clause_id) > 1
    ]

    return {
        "source_heading_count": len(source_ids),
        "parsed_clause_count": len(clauses),
        "missing": missing,
        "duplicates": duplicates,
        "malformed_headings": malformed_headings,
        "source_ids": source_id_values,
        "parsed_ids": parsed_ids,
    }


def print_audit(path: str | Path) -> None:
    result = audit_policy(path)

    print("Parser audit")
    print("------------")
    print(f"Clause headings found: {result['source_heading_count']}")
    print(f"Clauses parsed:        {result['parsed_clause_count']}")
    print(f"Missing:               {len(result['missing'])}")
    print(f"Duplicates:            {len(result['duplicates'])}")
    print(f"Malformed headings:    {len(result['malformed_headings'])}")

    if result["missing"]:
        print("\nMissing clauses:")

        for clause_id, line in result["missing"]:
            print(f"  {clause_id} at line {line}")

    if result["duplicates"]:
        print("\nDuplicate clause IDs:")

        for clause_id in result["duplicates"]:
            print(f"  {clause_id}")

    if result["malformed_headings"]:
        print("\nMalformed clause headings:")

        for item in result["malformed_headings"]:
            print(
                f"  {item['clause_id']} "
                f"at line {item['line']}: "
                f"{item['text']}"
            )

    if (
        not result["missing"]
        and not result["duplicates"]
        and not result["malformed_headings"]
        and result["source_heading_count"]
        == result["parsed_clause_count"]
    ):
        print("\nPASS: parser covered all detected clause headings.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse and audit the policy manual."
    )

    parser.add_argument(
        "path",
        nargs="?",
        default="data/policy-manual.md",
    )

    args = parser.parse_args()

    clauses = parse_policy(args.path)

    print(f"Parsed {len(clauses)} clauses.")

    for clause in clauses[:10]:
        print(
            f"{clause.clause_id} "
            f"(line {clause.line_no}): "
            f"{clause.text[:120]}"
        )

    print()
    print_audit(args.path)