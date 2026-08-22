from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .models import PolicyClause
from .parser import parse_policy
from .retrieval.hybrid_rank import HybridRetriever

DEFAULT_MODEL = "all-MiniLM-L6-v2"


@dataclass
class LocalIndex:
    clauses: list[PolicyClause]
    embeddings: np.ndarray
    model_name: str = DEFAULT_MODEL


def build_index(
    corpus_path: str | Path = "data/policy-manual.md",
    cache_path: str | Path = ".cache/index.pkl",
    model_name: str = DEFAULT_MODEL,
) -> LocalIndex:
    corpus_path = Path(corpus_path)
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    clauses = parse_policy(corpus_path)

    # Import here so parsing-only use does not load the embedding model.
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        [c.text for c in clauses],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    index = LocalIndex(
        clauses=clauses,
        embeddings=embeddings,
        model_name=model_name,
    )

    with cache_path.open("wb") as f:
        pickle.dump(index, f)

    return index


def load_or_build_index(
    corpus_path: str | Path = "data/policy-manual.md",
    cache_path: str | Path = ".cache/index.pkl",
    model_name: str = DEFAULT_MODEL,
) -> LocalIndex:
    corpus_path = Path(corpus_path)
    cache_path = Path(cache_path)

    if cache_path.exists() and cache_path.stat().st_mtime >= corpus_path.stat().st_mtime:
        try:
            with cache_path.open("rb") as f:
                index: LocalIndex = pickle.load(f)
            if index.model_name == model_name:
                return index
        except (OSError, pickle.PickleError, EOFError, AttributeError):
            pass

    return build_index(corpus_path, cache_path, model_name)


def create_retriever(
    corpus_path: str | Path = "data/policy-manual.md",
    cache_path: str | Path = ".cache/index.pkl",
    model_name: str = DEFAULT_MODEL,
) -> HybridRetriever:
    index = load_or_build_index(corpus_path, cache_path, model_name)
    return HybridRetriever(
        index.clauses,
        semantic_model=index.model_name,
        embeddings=index.embeddings,
    )
