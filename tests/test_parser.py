from pathlib import Path

from src.parser import parse_policy


def test_parser_extracts_clause_ids_and_metadata(tmp_path: Path):
    manual = tmp_path / "policy.md"
    manual.write_text(
        "# Part 2 — Eligibility\n"
        "## 2.1 Basic conditions\n"
        "\n"
        "**2.1.1** A person is eligible.\n"
        "\n"
        "**2.1.2(a)** The person must apply.\n",
        encoding="utf-8",
    )

    clauses = parse_policy(manual)

    assert [c.clause_id for c in clauses] == ["§2.1.1", "§2.1.2(a)"]
    assert clauses[0].part == "Part 2 — Eligibility"
    assert clauses[0].section == "2.1"
    assert clauses[0].line_no == 4


def test_parser_keeps_markdown_table_content(tmp_path: Path):
    manual = tmp_path / "policy.md"
    manual.write_text(
        "# Part 6 — Income\n"
        "## 6.6 Thresholds\n"
        "\n"
        "**6.6.1** The thresholds are —\n"
        "\n"
        "| Household size | Monthly threshold |\n"
        "|:--|:--|\n"
        "| 1 | $1,180 |\n"
        "| 2 | $1,590 |\n",
        encoding="utf-8",
    )

    clauses = parse_policy(manual)

    assert len(clauses) == 1
    assert "Household size | Monthly threshold" in clauses[0].text
    assert "1 | $1,180" in clauses[0].text


def test_parser_preserves_multiline_clause_text(tmp_path: Path):
    manual = tmp_path / "policy.md"
    manual.write_text(
        "# Part 1 — Definitions\n"
        "## 1.1 Purpose\n"
        "\n"
        "**1.1.1** First sentence.\n"
        "Second sentence continues the clause.\n",
        encoding="utf-8",
    )

    clauses = parse_policy(manual)

    assert len(clauses) == 1
    assert "First sentence." in clauses[0].text
    assert "Second sentence continues the clause." in clauses[0].text
