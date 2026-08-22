import numpy as np

from src.models import PolicyClause
from src.retrieval.hybrid_rank import HybridRetriever


class FakeSemanticRetriever:
    pass


def test_hybrid_retriever_returns_evidence(monkeypatch):
    clauses = [
        PolicyClause("§1.1.1", "income threshold household", "Part 1", "1.1", 1),
        PolicyClause("§1.1.2", "application deadline", "Part 1", "1.1", 2),
    ]

    # Keep this unit test deterministic without loading the transformer model.
    class FakeBM25:
        def __init__(self, clauses):
            self.clauses = clauses

        def search(self, query, top_k=10):
            return [(self.clauses[0], 3.0), (self.clauses[1], 1.0)]

    class FakeSemantic:
        def __init__(self, clauses, model_name=None, embeddings=None):
            self.clauses = clauses

        def search(self, query, top_k=10):
            return [(self.clauses[0], 0.9), (self.clauses[1], 0.2)]

    monkeypatch.setattr(
        "src.retrieval.hybrid_rank.BM25Retriever",
        FakeBM25,
    )
    monkeypatch.setattr(
        "src.retrieval.hybrid_rank.SemanticRetriever",
        FakeSemantic,
    )

    retriever = HybridRetriever(clauses, embeddings=np.zeros((2, 3)))
    results = retriever.search("income", top_k=2)

    assert len(results) == 2
    assert results[0].clause_id == "§1.1.1"
    assert results[0].fused_rank == 1
    assert "bm25" in results[0].retrieval_sources
    assert "semantic" in results[0].retrieval_sources
