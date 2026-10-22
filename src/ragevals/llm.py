"""Answer generation: a real Anthropic model, or an offline extractive fake.

Both implement the same ``Generator`` interface, so the API, the CLI and the eval suite never
know (or care) which one they are talking to. ``LLM_PROVIDER=fake`` is the default whenever
``ANTHROPIC_API_KEY`` is not set, which is what keeps tests and CI fully offline.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Protocol

from ragevals.store import RetrievedChunk
from ragevals.text import content_terms, unique

REFUSAL = "I don't know based on the FastAPI tutorial docs."

# USD per 1M tokens (input, output). Check https://docs.anthropic.com/en/docs/about-claude/pricing
# before trusting cost numbers; prices change.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


@dataclass
class Usage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        price_in, price_out = PRICES_PER_MTOK.get(self.model, (0.0, 0.0))
        return (self.input_tokens * price_in + self.output_tokens * price_out) / 1_000_000

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }


@dataclass
class Generation:
    text: str
    refused: bool
    cited: list[int] = field(default_factory=list)  # 1-based indices into the contexts
    usage: Usage = field(default_factory=lambda: Usage(model="none"))


class Generator(Protocol):
    name: str

    def generate(self, question: str, contexts: list[RetrievedChunk]) -> Generation: ...

    def stream(self, question: str, contexts: list[RetrievedChunk]) -> Iterator[str | Generation]:
        """Yield text deltas as they are produced, then the final ``Generation`` last."""
        ...


_CITATION_RE = re.compile(r"\[(\d+)\]")


def parse_citations(text: str, n_contexts: int) -> list[int]:
    """The distinct ``[n]`` markers in ``text`` that point at a real passage, in order."""
    return unique_ints(int(m) for m in _CITATION_RE.findall(text) if 1 <= int(m) <= n_contexts)


def unique_ints(values: Iterable[int]) -> list[int]:
    seen: list[int] = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen


def approx_tokens(text: str) -> int:
    """~4 characters per token: good enough for logging the fake model's "usage"."""
    return max(1, len(text) // 4)


# --- offline fake -------------------------------------------------------------------------------

# Words that appear in almost every question about this corpus and say nothing about the topic.
GENERIC_TERMS = frozenset(
    content_terms(
        "fastapi use uses used using how do does make work works way happen happens example "
        "docs tutorial need want app api python code write possible one two thing"
    )
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*\"(])")


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    in_fence = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not line or line.startswith("#"):
            continue
        if in_fence:
            sentences.append(line)
            continue
        line = re.sub(r"^[*-]\s+", "", line)
        sentences.extend(s.strip() for s in _SENTENCE_SPLIT_RE.split(line) if s.strip())
    return sentences


def question_terms(question: str) -> list[str]:
    return [t for t in unique(content_terms(question)) if t not in GENERIC_TERMS]


def context_support(question: str, contexts: list[RetrievedChunk], top_n: int = 3) -> float:
    """Fraction of the question's topical terms that appear anywhere in the top contexts.

    A cheap proxy for "is the answer in here?". Unanswerable questions tend to mention things
    the docs never talk about (``lambda``, ``websocket``...), which drags this number down.
    """
    terms = question_terms(question)
    if not terms or not contexts:
        return 0.0
    vocabulary = set(content_terms(" ".join(f"{c.heading} {c.content}" for c in contexts[:top_n])))
    return sum(t in vocabulary for t in terms) / len(terms)


class ExtractiveGenerator:
    """A deterministic stand-in for an LLM that answers by *quoting* the retrieved chunks.

    1. Refuse if the top chunks do not cover enough of the question's topical terms.
    2. Score every sentence of every retrieved chunk by IDF-weighted overlap with the question,
       discounted by the chunk's retrieval rank.
    3. Return the best few sentences in reading order, each followed by a ``[n]`` citation.

    It cannot paraphrase, reason, or combine facts, so it under-performs a real model on
    multi-hop questions. That is fine: its job is to exercise the pipeline end to end and to make
    answer quality *depend on retrieval quality*, which is what the offline evals measure.
    """

    name = "fake-extractive"

    def __init__(self, min_support: float = 0.6, max_sentences: int = 3) -> None:
        self.min_support = min_support
        self.max_sentences = max_sentences

    def generate(self, question: str, contexts: list[RetrievedChunk]) -> Generation:
        prompt_tokens = approx_tokens(question + "".join(c.content for c in contexts))
        if context_support(question, contexts) < self.min_support:
            return Generation(
                text=REFUSAL,
                refused=True,
                usage=Usage("fake", prompt_tokens, approx_tokens(REFUSAL)),
            )

        q_terms = set(question_terms(question))
        candidates: list[tuple[int, int, str, set[str]]] = []
        for rank, chunk in enumerate(contexts):
            for pos, sentence in enumerate(split_sentences(chunk.content)):
                if len(sentence) >= 25:
                    candidates.append((rank, pos, sentence, set(content_terms(sentence))))

        df = Counter(t for *_, terms in candidates for t in terms)
        n = max(1, len(candidates))

        def score(rank: int, terms: set[str]) -> float:
            overlap = sum(math.log(1 + n / df[t]) for t in q_terms & terms)
            return overlap / (1 + 0.25 * rank)

        scored = sorted(
            ((score(rank, terms), rank, pos, s) for rank, pos, s, terms in candidates),
            key=lambda x: (-x[0], x[1], x[2]),
        )
        best = [item for item in scored[: self.max_sentences] if item[0] > 0]
        if not best:
            return Generation(REFUSAL, True, usage=Usage("fake", prompt_tokens, 12))
        best.sort(key=lambda x: (x[1], x[2]))  # back into reading order
        text = " ".join(f"{s} [{rank + 1}]" for _, rank, _, s in best)
        return Generation(
            text=text,
            refused=False,
            cited=unique_ints(rank + 1 for _, rank, _, _ in best),
            usage=Usage("fake", prompt_tokens, approx_tokens(text)),
        )

    def stream(self, question: str, contexts: list[RetrievedChunk]) -> Iterator[str | Generation]:
        generation = self.generate(question, contexts)
        yield from re.split(r"(?<=\s)", generation.text)  # word by word, like a real stream
        yield generation


# --- Anthropic ----------------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You answer questions about the FastAPI tutorial using ONLY the numbered \
context passages provided by the user.

Rules:
- Cite every claim with the passage number in square brackets, like [1] or [2][3].
- Be concise: two to five sentences, unless a short list is clearer.
- If the passages do not contain the answer, reply with exactly: {REFUSAL}
- Do not use outside knowledge, even if you know the answer."""


def format_contexts(contexts: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[{i}] (file: {c.source} | section: {c.heading})\n{c.content}"
        for i, c in enumerate(contexts, start=1)
    )


def build_user_message(question: str, contexts: list[RetrievedChunk]) -> str:
    return f"Context passages:\n\n{format_contexts(contexts)}\n\nQuestion: {question}"


class AnthropicGenerator:
    """Grounded generation with Claude. Model from ``LLM_MODEL`` (default ``claude-sonnet-5-5``)."""

    def __init__(self, model: str | None = None, max_tokens: int = 8000) -> None:
        import anthropic

        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model = model or os.getenv("LLM_MODEL", "claude-sonnet-5-5")
        self.max_tokens = max_tokens
        self.name = f"anthropic:{self.model}"

    def _finish(self, text: str, usage, n_contexts: int) -> Generation:
        text = text.strip()
        return Generation(
            text=text,
            refused=REFUSAL.lower() in text.lower(),
            cited=parse_citations(text, n_contexts),
            usage=Usage(self.model, usage.input_tokens, usage.output_tokens),
        )

    def generate(self, question: str, contexts: list[RetrievedChunk]) -> Generation:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(question, contexts)}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return self._finish(text, response.usage, len(contexts))

    def stream(self, question: str, contexts: list[RetrievedChunk]) -> Iterator[str | Generation]:
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(question, contexts)}],
        ) as stream:
            yield from stream.text_stream
            final = stream.get_final_message()
        text = "".join(block.text for block in final.content if block.type == "text")
        yield self._finish(text, final.usage, len(contexts))


def llm_provider() -> str:
    default = "anthropic" if os.getenv("ANTHROPIC_API_KEY") else "fake"
    return os.getenv("LLM_PROVIDER", default).lower()


def get_generator(provider: str | None = None) -> Generator:
    provider = (provider or llm_provider()).lower()
    if provider == "fake":
        return ExtractiveGenerator()
    if provider == "anthropic":
        return AnthropicGenerator()
    raise ValueError(f"Unknown LLM_PROVIDER {provider!r} (expected fake or anthropic)")
