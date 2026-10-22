"""Named pipeline configurations. An eval run is always "one config against the golden set".

Each config changes *one* thing relative to the baseline (except ``combined``), so the results
table answers "what did this single change buy us?".
"""

from __future__ import annotations

from dataclasses import dataclass

from ragevals.chunking import Chunker, FixedSizeChunker, MarkdownHeadingChunker
from ragevals.embeddings import Embedder


@dataclass(frozen=True)
class PipelineConfig:
    name: str
    description: str
    chunker: str = "fixed"  # "fixed" | "markdown"
    retrieval: str = "vector"  # "vector" | "hybrid"
    reranker: str | None = None  # None | "lexical" | "cross-encoder" | "llm"
    k: int = 5  # chunks given to the generator (and the k in hit@k)
    candidates: int = 20  # how many chunks each first-stage retriever returns before fusion/rerank


CONFIGS: dict[str, PipelineConfig] = {
    "baseline": PipelineConfig(
        name="baseline",
        description="Fixed 800-char chunks, pgvector cosine top-5",
    ),
    "hybrid": PipelineConfig(
        name="hybrid",
        description="Baseline + Postgres full-text search, fused with RRF",
        retrieval="hybrid",
    ),
    "rerank": PipelineConfig(
        name="rerank",
        description="Baseline + rerank 20 vector candidates down to 5",
        reranker="lexical",
    ),
    "structured": PipelineConfig(
        name="structured",
        description="Baseline with structure-aware chunks (one per Markdown section)",
        chunker="markdown",
    ),
    "combined": PipelineConfig(
        name="combined",
        description="Structure-aware chunks + hybrid retrieval + rerank",
        chunker="markdown",
        retrieval="hybrid",
        reranker="lexical",
    ),
}


def get_config(name: str) -> PipelineConfig:
    try:
        return CONFIGS[name]
    except KeyError:
        raise ValueError(f"Unknown config {name!r}. Available: {', '.join(CONFIGS)}") from None


def make_chunker(kind: str) -> Chunker:
    if kind == "fixed":
        return FixedSizeChunker(size=800, overlap=100)
    if kind == "markdown":
        return MarkdownHeadingChunker(max_chars=1500, min_chars=250)
    raise ValueError(f"Unknown chunker {kind!r}")


def collection_name(config: PipelineConfig, embedder: Embedder) -> str:
    """Chunks are shared by every config with the same chunker + embedder."""
    return f"{make_chunker(config.chunker).name}__{embedder.name}"
