from __future__ import annotations

from rank_bm25 import BM25Okapi

from ..models import PolicyClause


class BM25Retriever:
    def __init__(self, clauses: list[PolicyClause]):
        self.clauses = clauses
        tokenized = [self._tokenize(c.text) for c in clauses]
        self.index = BM25Okapi(tokenized)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return text.lower().split()

    def search(self, query: str, top_k: int = 10) -> list[tuple[PolicyClause, float]]:
        scores = self.index.get_scores(self._tokenize(query))
        ranked = sorted(
            enumerate(scores),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        return [(self.clauses[i], float(score)) for i, score in ranked]
