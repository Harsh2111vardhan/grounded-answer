from src.models import Evidence, PolicyClause
from src.retrieval.cross_reference import CrossReferenceExpander


def test_expands_exact_clause_reference():
    clauses = [
        PolicyClause("§7.1.3", "See §3.2.2 for the exception.", "Part 7", "7.1", 1),
        PolicyClause("§3.2.2", "The period is extended to 90 days.", "Part 3", "3.2", 2),
    ]

    evidence = [
        Evidence(
            clause_id="§7.1.3",
            text=clauses[0].text,
            part=clauses[0].part,
            section=clauses[0].section,
            line_no=clauses[0].line_no,
            retrieval_sources=["bm25"],
        )
    ]

    result = CrossReferenceExpander(clauses).expand(evidence)

    assert [item.clause_id for item in result] == ["§7.1.3", "§3.2.2"]
    assert result[1].cross_reference_of == "§7.1.3"
    assert result[1].retrieval_sources == ["cross_reference"]


def test_expands_section_reference_to_nested_clauses():
    clauses = [
        PolicyClause("§7.1.3", "Full-time students see §5.4.", "Part 7", "7.1", 1),
        PolicyClause("§5.4.1", "Care allowance is disregarded.", "Part 5", "5.4", 2),
        PolicyClause("§5.4.2", "Care allowance does not alter household composition.", "Part 5", "5.4", 3),
        PolicyClause("§5.5.1", "Another rule.", "Part 5", "5.5", 4),
    ]

    evidence = [
        Evidence(
            clause_id="§7.1.3",
            text=clauses[0].text,
            part=clauses[0].part,
            section=clauses[0].section,
            line_no=clauses[0].line_no,
            retrieval_sources=["semantic"],
        )
    ]

    result = CrossReferenceExpander(clauses).expand(evidence)

    assert [item.clause_id for item in result] == [
        "§7.1.3",
        "§5.4.1",
        "§5.4.2",
    ]
    assert all(item.cross_reference_of == "§7.1.3" for item in result[1:])


def test_does_not_add_duplicate_retrieved_evidence():
    clauses = [
        PolicyClause("§7.1.3", "See §5.4.1.", "Part 7", "7.1", 1),
        PolicyClause("§5.4.1", "Care allowance is disregarded.", "Part 5", "5.4", 2),
    ]

    evidence = [
        Evidence(
            clause_id="§7.1.3",
            text=clauses[0].text,
            part=clauses[0].part,
            section=clauses[0].section,
            line_no=clauses[0].line_no,
            retrieval_sources=["bm25"],
        ),
        Evidence(
            clause_id="§5.4.1",
            text=clauses[1].text,
            part=clauses[1].part,
            section=clauses[1].section,
            line_no=clauses[1].line_no,
            retrieval_sources=["semantic"],
        ),
    ]

    result = CrossReferenceExpander(clauses).expand(evidence)

    assert len(result) == 2
    assert result[1].retrieval_sources == ["semantic"]
    assert result[1].cross_reference_of is None
