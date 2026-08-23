from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .models import Evidence, PolicyClause
from .parser import parse_policy
from .policy.amendments import apply_amendments, parse_amendment
from .policy.temporal import extract_temporal_context
from .retrieval.hybrid_rank import HybridRetriever

DEFAULT_MODEL = "all-MiniLM-L6-v2"


@dataclass
class LocalIndex:
    clauses: list[PolicyClause]
    embeddings: np.ndarray
    model_name: str = DEFAULT_MODEL
    amendments: tuple = ()
    amendment_paths: tuple[str, ...] = ()


def build_index(
    corpus_path: str | Path = "data/policy-manual.md",
    cache_path: str | Path = ".cache/index.pkl",
    model_name: str = DEFAULT_MODEL,
) -> LocalIndex:
    corpus_path = Path(corpus_path)
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    clauses = parse_policy(corpus_path)

    amendment_files = sorted(
        path
        for path in corpus_path.parent.glob("*.md")
        if path.resolve() != corpus_path.resolve()
    )

    amendments = tuple(
        parse_amendment(path)
        for path in amendment_files
    )

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)

    embeddings = model.encode(
        [clause.text for clause in clauses],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    index = LocalIndex(
        clauses=clauses,
        embeddings=embeddings,
        model_name=model_name,
        amendments=amendments,
        amendment_paths=tuple(
            str(path)
            for path in amendment_files
        ),
    )

    with cache_path.open("wb") as file:
        pickle.dump(index, file)

    return index


def load_or_build_index(
    corpus_path: str | Path = "data/policy-manual.md",
    cache_path: str | Path = ".cache/index.pkl",
    model_name: str = DEFAULT_MODEL,
) -> LocalIndex:
    corpus_path = Path(corpus_path)
    cache_path = Path(cache_path)

    amendment_files = sorted(
        path
        for path in corpus_path.parent.glob("*.md")
        if path.resolve() != corpus_path.resolve()
    )

    source_mtimes = [
        corpus_path.stat().st_mtime
    ]

    source_mtimes.extend(
        path.stat().st_mtime
        for path in amendment_files
    )

    newest_source = max(source_mtimes)

    if (
        cache_path.exists()
        and cache_path.stat().st_mtime >= newest_source
    ):
        try:
            with cache_path.open("rb") as file:
                index: LocalIndex = pickle.load(file)

            if (
                index.model_name == model_name
                and hasattr(index, "amendments")
                and tuple(
                    getattr(
                        index,
                        "amendment_paths",
                        (),
                    )
                )
                == tuple(
                    str(path)
                    for path in amendment_files
                )
            ):
                return index

        except (
            OSError,
            pickle.PickleError,
            EOFError,
            AttributeError,
        ):
            pass

    return build_index(
        corpus_path,
        cache_path,
        model_name,
    )


class TemporalRetriever:
    def __init__(
        self,
        index: LocalIndex,
    ):
        self.index = index
        self._retrievers = {}

    def _resolved_clauses(
        self,
        question: str,
    ) -> tuple[list[PolicyClause], set[str]]:
        context = extract_temporal_context(
            question
        )

        clauses = apply_amendments(
            self.index.clauses,
            list(self.index.amendments),
            event_date=context.event_date,
            determination_date=context.determination_date,
        )

        amendment_clause_ids: set[str] = set()

        for amendment in self.index.amendments:
            for change in amendment.changes:
                if change.applicability_basis == "event":
                    selected_date = context.event_date
                elif (
                    change.applicability_basis
                    == "determination"
                ):
                    selected_date = context.determination_date
                else:
                    selected_date = (
                        context.event_date
                        or context.determination_date
                    )

                if (
                    selected_date is not None
                    and selected_date
                    >= change.effective_date
                ):
                    if change.target_clause_id:
                        amendment_clause_ids.add(
                            change.target_clause_id
                        )

                    if change.inserted_clause_id:
                        amendment_clause_ids.add(
                            change.inserted_clause_id
                        )

        return clauses, amendment_clause_ids

    @staticmethod
    def _evidence_from_clause(
        clause: PolicyClause,
        rank: int,
    ) -> Evidence:
        return Evidence(
            clause_id=clause.clause_id,
            text=clause.text,
            part=clause.part,
            section=clause.section,
            line_no=clause.line_no,
            fused_rank=rank,
            retrieval_sources=["amendment"],
        )

    def search(
        self,
        question: str,
        top_k: int = 8,
        candidate_k: int | None = None,
        rrf_k: int = 60,
    ):
        from sentence_transformers import SentenceTransformer

        clauses, amendment_clause_ids = (
            self._resolved_clauses(question)
        )

        key = tuple(
            (
                clause.clause_id,
                clause.text,
            )
            for clause in clauses
        )

        retriever = self._retrievers.get(key)

        if retriever is None:
            model = SentenceTransformer(
                self.index.model_name
            )

            embeddings = model.encode(
                [
                    clause.text
                    for clause in clauses
                ],
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )

            retriever = HybridRetriever(
                clauses,
                semantic_model=self.index.model_name,
                embeddings=embeddings,
            )

            self._retrievers[key] = retriever

        results = retriever.search(
            question,
            top_k=top_k,
            candidate_k=candidate_k,
            rrf_k=rrf_k,
        )

        if not amendment_clause_ids:
            return results

        existing_ids = {
            evidence.clause_id
            for evidence in results
        }

        clause_by_id = {
            clause.clause_id: clause
            for clause in clauses
        }

        missing_amended = [
            clause_by_id[clause_id]
            for clause_id in amendment_clause_ids
            if (
                clause_id in clause_by_id
                and clause_id not in existing_ids
            )
        ]

        if not missing_amended:
            return results

        next_rank = len(results) + 1

        amendment_evidence = [
            self._evidence_from_clause(
                clause,
                next_rank + index,
            )
            for index, clause in enumerate(
                missing_amended
            )
        ]

        results.extend(
            amendment_evidence
        )

        return results


def create_retriever(
    corpus_path: str | Path = "data/policy-manual.md",
    cache_path: str | Path = ".cache/index.pkl",
    model_name: str = DEFAULT_MODEL,
) -> TemporalRetriever:
    index = load_or_build_index(
        corpus_path,
        cache_path,
        model_name,
    )

    return TemporalRetriever(index)