from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from ..models import PolicyClause


class SemanticRetriever:
    def __init__(
        self,
        clauses: list[PolicyClause],
        model_name: str = "all-MiniLM-L6-v2",
        embeddings: np.ndarray | None = None,
    ):
        self.clauses = clauses
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

        if embeddings is None:
            self.embeddings = self.model.encode(
                [c.text for c in clauses],
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        else:
            self.embeddings = embeddings

    def search(self, query: str, top_k: int = 10) -> list[tuple[PolicyClause, float]]:
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]

        scores = self.embeddings @ query_embedding
        ranked = np.argsort(scores)[::-1][:top_k]

        return [
            (self.clauses[int(i)], float(scores[int(i)]))
            for i in ranked
        ]
