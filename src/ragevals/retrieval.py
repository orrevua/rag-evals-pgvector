"""Retrievers: question -> ranked chunks. Every strategy implements ``Retriever``."""

from __future__ import annotations

from typing import Protocol

from ragevals.embeddings import Embedder
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
