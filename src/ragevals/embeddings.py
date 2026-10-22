"""Embedders: text -> vector. One small interface, three implementations.

* ``hash``      Deterministic hashing-trick vectors. Offline, instant, no model download. It is a
                bag-of-words in disguise (no semantics: "car" and "automobile" are unrelated),
                which is why the offline numbers are a *floor*, not a forecast.
* ``fastembed`` Local ONNX sentence embeddings (default ``BAAI/bge-small-en-v1.5``, 384 dims).
                ``uv sync --extra fastembed``; downloads the model from Hugging Face on first use.
* ``openai``    ``text-embedding-3-small`` (1536 dims).
                ``uv sync --extra openai`` and set ``OPENAI_API_KEY``.

Vectors are L2-normalised so cosine similarity == dot product, which is what pgvector's ``<=>``
(cosine distance) operator assumes is meaningful.
"""

from __future__ import annotations

import hashlib
import math
import os
from collections import Counter
from typing import Protocol

import numpy as np

from ragevals.text import content_terms


class Embedder(Protocol):
    name: str  # used in the collection name, so different embedders never mix vectors
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _normalize(vec: np.ndarray) -> list[float]:
    norm = float(np.linalg.norm(vec))
    return (vec / norm).tolist() if norm > 0 else vec.tolist()


class HashEmbedder:
    """The "hashing trick": each feature is hashed to one of ``dim`` buckets with a +/- sign.

    Features are stemmed content words plus adjacent-word bigrams (bigrams capture a bit of word
    order: "path parameter" vs "parameter path"). ``blake2b`` is used instead of Python's
    ``hash()`` because the latter is randomised per process, and we need the same vector for the
    same text in every run, on every machine.
    """

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.name = f"hash{dim}"

    def _bucket(self, feature: str) -> tuple[int, float]:
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        value = int.from_bytes(digest, "little")
        return value % self.dim, (1.0 if (value >> 63) & 1 else -1.0)

    def _embed(self, text: str) -> list[float]:
        terms = content_terms(text)
        features = Counter(terms)
        features.update(f"{a} {b}" for a, b in zip(terms, terms[1:], strict=False))
        vec = np.zeros(self.dim, dtype=np.float64)
        for feature, count in features.items():
            index, sign = self._bucket(feature)
            weight = 1.0 + math.log(count)  # sublinear term frequency
            if " " in feature:
                weight *= 0.5  # bigrams are supporting evidence, not the main signal
            vec[index] += sign * weight
        return _normalize(vec)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class FastEmbedEmbedder:
    """Local sentence embeddings via ``fastembed`` (ONNX Runtime, no PyTorch)."""

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5") -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError("Install the extra: uv sync --extra fastembed") from exc
        self._model = TextEmbedding(model_name=model)
        self.dim = len(next(iter(self._model.embed(["dimension probe"]))))
        self.name = "fastembed-" + model.split("/")[-1]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_normalize(np.asarray(v)) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        # BGE models are trained with a query prefix; fastembed's query_embed applies it.
        return _normalize(np.asarray(next(iter(self._model.query_embed(text)))))


class OpenAIEmbedder:
    """Hosted embeddings. Batches requests; the API returns normalised vectors already."""

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError("Install the extra: uv sync --extra openai") from exc
        self._client = OpenAI()
        self._model = model
        self.dim = 1536 if model.endswith("small") else 3072
        self.name = "openai-" + model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), 128):
            response = self._client.embeddings.create(model=self._model, input=texts[i : i + 128])
            vectors.extend(item.embedding for item in response.data)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def get_embedder(kind: str | None = None) -> Embedder:
    """Build the embedder named by ``kind`` or the ``EMBEDDER`` env var (default: ``hash``)."""
    kind = (kind or os.getenv("EMBEDDER", "hash")).lower()
    if kind == "hash":
        return HashEmbedder(dim=int(os.getenv("HASH_DIM", "512")))
    if kind == "fastembed":
        return FastEmbedEmbedder(os.getenv("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5"))
    if kind == "openai":
        return OpenAIEmbedder(os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))
    raise ValueError(f"Unknown embedder {kind!r} (expected hash, fastembed or openai)")
