"""Named pipeline configurations. An eval run is always "one config against the golden set".

Each config changes *one* thing relative to the baseline (except ``combined``), so the results
table answers "what did this single change buy us?".
"""

from __future__ import annotations

from dataclasses import dataclass

from ragevals.chunking import Chunker, FixedSizeChunker
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
}


def get_config(name: str) -> PipelineConfig:
    try:
        return CONFIGS[name]
    except KeyError:
        raise ValueError(f"Unknown config {name!r}. Available: {', '.join(CONFIGS)}") from None


def make_chunker(kind: str) -> Chunker:
    if kind == "fixed":
        return FixedSizeChunker(size=800, overlap=100)
    raise ValueError(f"Unknown chunker {kind!r}")


def collection_name(config: PipelineConfig, embedder: Embedder) -> str:
    """Chunks are shared by every config with the same chunker + embedder."""
    return f"{make_chunker(config.chunker).name}__{embedder.name}"
