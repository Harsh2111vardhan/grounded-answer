import numpy as np

from src.models import PolicyClause
from src.retrieval.hybrid_rank import HybridRetriever


def test_hybrid_search_expands_references(monkeypatch):
    clauses = [
        PolicyClause(
            "§7.1.3",
            "Full-time students see §5.4.",
            "Part 7",
            "7.1",
            1,
        ),
        PolicyClause(
            "§5.4.1",
            "A care allowance is disregarded.",
            "Part 5",
            "5.4",
            2,
        ),
    ]

    class FakeBM25:
        def __init__(self, clauses):
            self.clauses = clauses

        def search(self, query, top_k=10):
            return [(self.clauses[0], 3.0)]

    class FakeSemantic:
        def __init__(self, clauses, model_name=None, embeddings=None):
            self.clauses = clauses

        def search(self, query, top_k=10):
            return [(self.clauses[0], 0.9)]

    monkeypatch.setattr(
        "src.retrieval.hybrid_rank.BM25Retriever",
        FakeBM25,
    )
    monkeypatch.setattr(
        "src.retrieval.hybrid_rank.SemanticRetriever",
        FakeSemantic,
    )

    retriever = HybridRetriever(
        clauses,
        embeddings=np.zeros((2, 3)),
    )

    results = retriever.search("full-time students", top_k=1)

    assert results[0].clause_id == "§7.1.3"
    assert results[1].clause_id == "§5.4.1"
    assert results[1].cross_reference_of == "§7.1.3"
