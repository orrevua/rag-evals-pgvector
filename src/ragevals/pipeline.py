"""The RAG pipeline: retrieve -> generate -> cite. Wires a config to concrete components."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field

from ragevals.configs import PipelineConfig, collection_name
from ragevals.embeddings import Embedder
from ragevals.llm import Generation, Generator, Usage
from ragevals.rerank import get_reranker
from ragevals.retrieval import (
    HybridRetriever,
    KeywordRetriever,
    RerankingRetriever,
    Retriever,
    VectorRetriever,
)
from ragevals.store import PgVectorStore, RetrievedChunk
from ragevals.text import TermStats


@dataclass
class Source:
    source: str
    heading: str
    chunk_key: str
    score: float


@dataclass
class Answer:
    question: str
    answer: str
    refused: bool
    sources: list[Source]
    config: str
    generator: str
    usage: Usage
    retrieved: list[RetrievedChunk] = field(default_factory=list)
    timings_ms: dict[str, float] = field(default_factory=dict)

    def to_dict(self, include_retrieved: bool = False) -> dict:
        data = {
            "question": self.question,
            "answer": self.answer,
            "refused": self.refused,
            "sources": [asdict(s) for s in self.sources],
            "config": self.config,
            "generator": self.generator,
            "usage": self.usage.to_dict(),
            "timings_ms": self.timings_ms,
        }
        if include_retrieved:
            data["retrieved"] = [asdict(c) for c in self.retrieved]
        return data


def cited_sources(generation: Generation, contexts: list[RetrievedChunk]) -> list[Source]:
    """Map ``[n]`` citations back to chunks. No citations -> cite everything we showed the model."""
    if generation.refused:
        return []
    indices = generation.cited or list(range(1, len(contexts) + 1))
    return [
        Source(
            contexts[i - 1].source,
            contexts[i - 1].heading,
            contexts[i - 1].chunk_key,
            round(contexts[i - 1].score, 4),
        )
        for i in indices
    ]


class RagPipeline:
    def __init__(self, config: PipelineConfig, retriever: Retriever, generator: Generator) -> None:
        self.config = config
        self.retriever = retriever
        self.generator = generator

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        return self.retriever.retrieve(question, self.config.k)

    def answer(self, question: str) -> Answer:
        t0 = time.perf_counter()
        contexts = self.retrieve(question)
        t1 = time.perf_counter()
        generation = self.generator.generate(question, contexts)
        t2 = time.perf_counter()
        return Answer(
            question=question,
            answer=generation.text,
            refused=generation.refused,
            sources=cited_sources(generation, contexts),
            config=self.config.name,
            generator=self.generator.name,
            usage=generation.usage,
            retrieved=contexts,
            timings_ms={
                "retrieval": round((t1 - t0) * 1000, 2),
                "generation": round((t2 - t1) * 1000, 2),
                "total": round((t2 - t0) * 1000, 2),
            },
        )

    def stream(self, question: str) -> Iterator[str | Answer]:
        """Yield text deltas, then the complete ``Answer`` (same shape as ``answer()``)."""
        t0 = time.perf_counter()
        contexts = self.retrieve(question)
        t1 = time.perf_counter()
        for item in self.generator.stream(question, contexts):
            if isinstance(item, Generation):
                t2 = time.perf_counter()
                yield Answer(
                    question=question,
                    answer=item.text,
                    refused=item.refused,
                    sources=cited_sources(item, contexts),
                    config=self.config.name,
                    generator=self.generator.name,
                    usage=item.usage,
                    retrieved=contexts,
                    timings_ms={
                        "retrieval": round((t1 - t0) * 1000, 2),
                        "generation": round((t2 - t1) * 1000, 2),
                        "total": round((t2 - t0) * 1000, 2),
                    },
                )
            else:
                yield item


def build_retriever(
    config: PipelineConfig,
    store: PgVectorStore,
    embedder: Embedder,
    stats: TermStats | None = None,
) -> Retriever:
    collection = collection_name(config, embedder)
    vector = VectorRetriever(store, embedder, collection)
    retriever: Retriever
    if config.retrieval == "vector":
        retriever = vector
    elif config.retrieval == "hybrid":
        retriever = HybridRetriever(vector, KeywordRetriever(store, collection), config.candidates)
    else:
        raise ValueError(f"Unknown retrieval strategy {config.retrieval!r}")
    if config.reranker:
        retriever = RerankingRetriever(
            retriever, get_reranker(config.reranker, stats), config.candidates
        )
    return retriever


def build_pipeline(
    config: PipelineConfig,
    store: PgVectorStore,
    embedder: Embedder,
    generator: Generator,
    stats: TermStats | None = None,
) -> RagPipeline:
    """``stats`` (corpus IDF, see ``corpus.corpus_stats``) feeds the lexical reranker."""
    return RagPipeline(config, build_retriever(config, store, embedder, stats), generator)
