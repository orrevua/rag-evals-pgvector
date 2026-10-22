"""Retrievers: question -> ranked chunks. Every strategy implements ``Retriever``."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from ragevals.embeddings import Embedder
from ragevals.rerank import Reranker
from ragevals.store import PgVectorStore, RetrievedChunk


class Retriever(Protocol):
    def retrieve(self, question: str, k: int) -> list[RetrievedChunk]: ...


class VectorRetriever:
    """Dense retrieval: embed the question, return the k nearest chunks by cosine similarity."""

    def __init__(self, store: PgVectorStore, embedder: Embedder, collection: str) -> None:
        self.store = store
        self.embedder = embedder
        self.collection = collection

    def retrieve(self, question: str, k: int) -> list[RetrievedChunk]:
        return self.store.vector_search(self.collection, self.embedder.embed_query(question), k)


def reciprocal_rank_fusion(
    rankings: list[list[RetrievedChunk]], k: int, rrf_k: int = 60
) -> list[RetrievedChunk]:
    """Merge ranked lists by summing ``1 / (rrf_k + rank)`` for every list a chunk appears in.

    RRF only looks at *ranks*, never at raw scores, which is exactly what you want when fusing a
    cosine similarity (0..1) with a ``ts_rank`` (unbounded, different distribution). ``rrf_k=60``
    is the constant from the original paper (Cormack et al., 2009); it damps the advantage of
    the very top ranks so that agreement between retrievers matters more.
    """
    scores: dict[str, float] = {}
    chunks: dict[str, RetrievedChunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk.chunk_key] = scores.get(chunk.chunk_key, 0.0) + 1.0 / (rrf_k + rank)
            chunks.setdefault(chunk.chunk_key, chunk)
    ordered = sorted(scores, key=lambda key: (-scores[key], key))[:k]
    return [replace(chunks[key], score=round(scores[key], 6)) for key in ordered]


class KeywordRetriever:
    """Sparse retrieval with Postgres full-text search (see ``PgVectorStore.keyword_search``)."""

    def __init__(self, store: PgVectorStore, collection: str) -> None:
        self.store = store
        self.collection = collection

    def retrieve(self, question: str, k: int) -> list[RetrievedChunk]:
        return self.store.keyword_search(self.collection, question, k)


class HybridRetriever:
    """Dense + sparse, fused with RRF.

    Vectors are good at "same meaning, different words"; full-text search is good at exact
    identifiers (``response_model_exclude_unset``, ``HTTPException``) that embeddings blur.
    Each side returns ``candidates`` chunks and RRF picks the top k.
    """

    def __init__(
        self, vector: VectorRetriever, keyword: KeywordRetriever, candidates: int = 20
    ) -> None:
        self.vector = vector
        self.keyword = keyword
        self.candidates = candidates

    def retrieve(self, question: str, k: int) -> list[RetrievedChunk]:
        return reciprocal_rank_fusion(
            [
                self.vector.retrieve(question, self.candidates),
                self.keyword.retrieve(question, self.candidates),
            ],
            k=k,
        )


class RerankingRetriever:
    """Two-stage retrieval: ``base`` fetches ``candidates``, ``reranker`` keeps the best k."""

    def __init__(self, base: Retriever, reranker: Reranker, candidates: int = 20) -> None:
        self.base = base
        self.reranker = reranker
        self.candidates = candidates

    def retrieve(self, question: str, k: int) -> list[RetrievedChunk]:
        candidates = self.base.retrieve(question, max(k, self.candidates))
        return self.reranker.rerank(question, candidates)[:k]
