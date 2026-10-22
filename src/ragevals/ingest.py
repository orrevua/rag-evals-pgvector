"""Ingestion: corpus -> chunks -> embeddings -> pgvector, one collection per chunker+embedder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ragevals.configs import PipelineConfig, collection_name, make_chunker
from ragevals.corpus import load_corpus
from ragevals.embeddings import Embedder
from ragevals.store import PgVectorStore


@dataclass
class IngestResult:
    collection: str
    documents: int
    chunks: int


def ingest(
    store: PgVectorStore,
    embedder: Embedder,
    configs: list[PipelineConfig],
    corpus_dir: Path,
) -> list[IngestResult]:
    documents = load_corpus(corpus_dir)
    if not documents:
        raise RuntimeError(f"No Markdown files found under {corpus_dir}")
    results: list[IngestResult] = []
    done: set[str] = set()
    for config in configs:
        collection = collection_name(config, embedder)
        if collection in done:
            continue  # several configs share the same chunks
        chunker = make_chunker(config.chunker)
        chunks = [chunk for doc in documents for chunk in chunker.chunk(doc)]
        # Embed heading + content: the heading is often the best summary of what a chunk is about.
        embeddings = embedder.embed_documents([f"{c.heading}\n{c.content}" for c in chunks])
        store.replace_collection(
            collection,
            chunker=chunker.name,
            embedder=embedder.name,
            dim=embedder.dim,
            chunks=chunks,
            embeddings=embeddings,
        )
        results.append(IngestResult(collection, len(documents), len(chunks)))
        done.add(collection)
    return results
