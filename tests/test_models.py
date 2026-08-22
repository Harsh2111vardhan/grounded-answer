from src.models import Evidence, PolicyClause


def test_policy_clause_stores_source_information():
    clause = PolicyClause(
        clause_id="§4.3.2",
        text="A recipient must report a change.",
        part="Part 4 — Exclusions",
        section="4.3",
        line_no=42,
    )

    assert clause.clause_id == "§4.3.2"
    assert clause.line_no == 42


def test_evidence_tracks_retrieval_sources():
    evidence = Evidence(
        clause_id="§4.3.2",
        text="A recipient must report a change.",
        part="Part 4 — Exclusions",
        section="4.3",
        line_no=42,
        retrieval_sources=["bm25", "semantic"],
    )

    assert "bm25" in evidence.retrieval_sources
    assert "semantic" in evidence.retrieval_sources
