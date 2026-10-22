"""Rerankers: reorder a first-stage candidate list with a more careful (and more expensive) scorer.

The classic two-stage pattern: a cheap retriever fetches ~20 candidates with high recall, then a
reranker that looks at the question and each candidate *together* picks the best k. Embeddings
score question and chunk independently; a cross-encoder or LLM reads them jointly, which is
why reranking usually improves precision at the top of the list.

* ``lexical``       BM25 over the candidates, with corpus IDF and a heading boost. Offline.
* ``cross-encoder`` ``fastembed`` TextCrossEncoder (``Xenova/ms-marco-MiniLM-L-6-v2``).
* ``llm``           Ask the fast Claude model to rank the candidates.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from dataclasses import replace
from typing import Protocol

from ragevals.llm import question_terms
from ragevals.store import RetrievedChunk
from ragevals.text import TermStats, content_terms


class Reranker(Protocol):
    name: str

    def rerank(self, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]: ...


def _reorder(chunks: list[RetrievedChunk], scores: list[float]) -> list[RetrievedChunk]:
    # Stable sort: ties keep the first-stage order.
    order = sorted(range(len(chunks)), key=lambda i: -scores[i])
    return [replace(chunks[i], score=round(float(scores[i]), 6)) for i in order]


class LexicalReranker:
    """BM25 restricted to the candidate set, using corpus-wide IDF.

    The heading is counted twice: a question about "Response Status Code" should prefer the chunk
    *titled* that over one that merely mentions it. ``k1`` controls term-frequency saturation and
    ``b`` length normalisation (the textbook defaults).
    """

    name = "lexical"

    def __init__(self, stats: TermStats | None = None, k1: float = 1.2, b: float = 0.75) -> None:
        self.stats = stats
        self.k1 = k1
        self.b = b

    def rerank(self, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return []
        q_terms = question_terms(question)
        docs = [Counter(content_terms(f"{c.heading} {c.heading} {c.content}")) for c in chunks]
        lengths = [sum(d.values()) for d in docs]
        avg_len = sum(lengths) / len(lengths) or 1.0
        local_df = Counter(t for d in docs for t in d)

        def idf(term: str) -> float:
            if self.stats:
                return self.stats.idf(term)
            return math.log(1 + len(docs) / (local_df[term] or 0.5))

        scores = []
        for doc, length in zip(docs, lengths, strict=True):
            score = 0.0
            for term in q_terms:
                tf = doc.get(term, 0)
                if tf:
                    norm = self.k1 * (1 - self.b + self.b * length / avg_len)
                    score += idf(term) * tf * (self.k1 + 1) / (tf + norm)
            scores.append(score)
        return _reorder(chunks, scores)


class CrossEncoderReranker:
    """A small cross-encoder via fastembed (ONNX). ``uv sync --extra fastembed``."""

    def __init__(self, model: str = "Xenova/ms-marco-MiniLM-L-6-v2") -> None:
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError("Install the extra: uv sync --extra fastembed") from exc
        self._model = TextCrossEncoder(model_name=model)
        self.name = "cross-encoder:" + model.split("/")[-1]

    def rerank(self, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return []
        texts = [f"{c.heading}\n{c.content}" for c in chunks]
        scores = list(self._model.rerank(question, texts))
        return _reorder(chunks, scores)


LLM_RERANK_PROMPT = """Rank documentation passages by how well they answer a question.

Question: {question}

Passages:
{passages}

Reply with JSON only: a list of passage numbers, most relevant first, including every passage.
Example: [3, 1, 2]"""


class LLMReranker:
    """Listwise reranking with the fast Claude model (``LLM_FAST_MODEL``)."""

    def __init__(self, model: str | None = None) -> None:
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("LLM_FAST_MODEL", "claude-haiku-5-5")
        self.name = f"llm:{self.model}"

    def rerank(self, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return []
        passages = "\n\n".join(
            f"[{i}] ({c.source} | {c.heading})\n{c.content[:1200]}"
            for i, c in enumerate(chunks, start=1)
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": LLM_RERANK_PROMPT.format(question=question, passages=passages),
                }
            ],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        order = parse_ranking(text, len(chunks))
        # Turn the ranking into scores so the output looks like every other reranker's.
        scores = [0.0] * len(chunks)
        for position, index in enumerate(order):
            scores[index] = float(len(chunks) - position)
        return _reorder(chunks, scores)


def parse_ranking(text: str, n: int) -> list[int]:
    """0-based indices from a reply like "[3, 1, 2]"; missing ones keep their original order."""
    ranked: list[int] = []
    match = re.search(r"\[[\d,\s]*\]", text)
    if match:
        try:
            for value in json.loads(match.group(0)):
                index = int(value) - 1
                if 0 <= index < n and index not in ranked:
                    ranked.append(index)
        except ValueError:
            pass
    return ranked + [i for i in range(n) if i not in ranked]


def get_reranker(kind: str, stats: TermStats | None = None) -> Reranker:
    """``kind`` comes from the config; the ``RERANKER`` env var overrides it."""
    kind = os.getenv("RERANKER", kind).lower()
    if kind == "lexical":
        return LexicalReranker(stats)
    if kind == "cross-encoder":
        return CrossEncoderReranker(
            os.getenv("CROSS_ENCODER_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2")
        )
    if kind == "llm":
        return LLMReranker()
    raise ValueError(f"Unknown reranker {kind!r} (expected lexical, cross-encoder or llm)")
