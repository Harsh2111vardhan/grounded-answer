import pytest

from src.models import PolicyClause
from src.retrieval.lexical import BM25Retriever


@pytest.fixture
def clauses():
    return [
        PolicyClause(
            "§2.1.1",
            "A person is eligible for assistance if the conditions are satisfied.",
            "Part 2 — Eligibility",
            "2.1",
            10,
        ),
        PolicyClause(
            "§6.6.1",
            "A household is not eligible where countable income exceeds the applicable threshold.",
            "Part 6 — Income",
            "6.6",
            20,
        ),
        PolicyClause(
            "§8.1.1",
            "An application may be made online, in person, by telephone, or in writing.",
            "Part 8 — Applications",
            "8.1",
            30,
        ),
    ]


def test_bm25_returns_relevant_clause(clauses):
    retriever = BM25Retriever(clauses)

    results = retriever.search("income threshold", top_k=2)

    assert results[0][0].clause_id == "§6.6.1"


def test_bm25_returns_requested_number(clauses):
    retriever = BM25Retriever(clauses)

    results = retriever.search("application", top_k=2)

    assert len(results) == 2
