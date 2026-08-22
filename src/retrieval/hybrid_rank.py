from __future__ import annotations

from ..models import Evidence, PolicyClause
from .cross_reference import CrossReferenceExpander
from .lexical import BM25Retriever
from .semantic import SemanticRetriever


class HybridRetriever:
    def __init__(
        self,
        clauses: list[PolicyClause],
        semantic_model: str = "all-MiniLM-L6-v2",
        embeddings=None,
    ):
        self.clauses = clauses
        self.lexical = BM25Retriever(clauses)
        self.semantic = SemanticRetriever(
            clauses,
            model_name=semantic_model,
            embeddings=embeddings,
        )
        self.cross_reference = CrossReferenceExpander(clauses)

    def search(
        self,
        query: str,
        top_k: int = 8,
        candidate_k: int | None = None,
        rrf_k: int = 60,
    ) -> list[Evidence]:
        candidate_k = candidate_k or max(top_k * 3, 20)

        lexical_results = self.lexical.search(query, candidate_k)
        semantic_results = self.semantic.search(query, candidate_k)

        lexical_scores = {
            clause.clause_id: score
            for clause, score in lexical_results
        }
        semantic_scores = {
            clause.clause_id: score
            for clause, score in semantic_results
        }
        clauses_by_id = {
            clause.clause_id: clause
            for clause in self.clauses
        }

        rrf_scores: dict[str, float] = {}
        sources: dict[str, set[str]] = {}

        for rank, (clause, _) in enumerate(lexical_results, start=1):
            rrf_scores[clause.clause_id] = (
                rrf_scores.get(clause.clause_id, 0.0)
                + 1.0 / (rrf_k + rank)
            )
            sources.setdefault(clause.clause_id, set()).add("bm25")

        for rank, (clause, _) in enumerate(semantic_results, start=1):
            rrf_scores[clause.clause_id] = (
                rrf_scores.get(clause.clause_id, 0.0)
                + 1.0 / (rrf_k + rank)
            )
            sources.setdefault(clause.clause_id, set()).add("semantic")

        ranked_ids = sorted(
            rrf_scores,
            key=lambda clause_id: rrf_scores[clause_id],
            reverse=True,
        )[:top_k]

        evidence: list[Evidence] = []

        for rank, clause_id in enumerate(ranked_ids, start=1):
            clause = clauses_by_id[clause_id]

            evidence.append(
                Evidence(
                    clause_id=clause.clause_id,
                    text=clause.text,
                    part=clause.part,
                    section=clause.section,
                    line_no=clause.line_no,
                    bm25_score=lexical_scores.get(clause_id),
                    semantic_score=semantic_scores.get(clause_id),
                    fused_rank=rank,
                    retrieval_sources=sorted(sources[clause_id]),
                )
            )

        # Expand only one hop. Referenced evidence is deliberately marked
        # separately so later grounding/citation logic knows why it exists.
        return self.cross_reference.expand(evidence)
