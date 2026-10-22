"""Tiny text utilities shared by the hashing embedder, the rerankers, the fake LLM and the metrics.

Everything here is deliberately simple so you can read it in one sitting.
Real systems would use the embedding model's own tokenizer; here a regex tokenizer plus the
Snowball stemmer is enough. The point is a *deterministic* and *plausible* offline pipeline.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

import snowballstemmer

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")

# A compact English stopword list plus question words. Kept short on purpose.
STOPWORDS: frozenset[str] = frozenset(
    """
    a an and are as at be been being but by can could did do does doing for from had has have
    having he her here hers him his how i if in into is it its itself just me more most my no nor
    not of off on once only or other our ours out over own same she should so some such than that
    the their theirs them then there these they this those through to too under until up very was
    we were what when where which while who whom why will with would you your yours yourself
    also any each few both again further s t don shouldn now get got let like
    """.split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens. ``max_length`` stays one token *and* also yields its parts."""
    tokens: list[str] = []
    for match in _TOKEN_RE.finditer(text.lower()):
        token = match.group(0)
        tokens.append(token)
        if "_" in token:
            tokens.extend(part for part in token.split("_") if part)
    return tokens


_STEMMER = snowballstemmer.stemmer("english")


@lru_cache(maxsize=65536)
def stem(token: str) -> str:
    """Snowball (Porter2) stemming: "parameters" -> "paramet", "cookies" -> "cooki".

    It only needs to be *consistent*: queries and documents go through the same function.
    It is the same algorithm Postgres uses for ``to_tsvector('english', ...)``.
    """
    if "_" in token or token.isdigit():
        return token  # identifiers like max_length and numbers stay as they are
    return _STEMMER.stemWord(token)


def content_terms(text: str) -> list[str]:
    """Stemmed tokens with stopwords removed: the "meaningful words" of a text."""
    return [stem(t) for t in tokenize(text) if t not in STOPWORDS]


def normalize(text: str) -> str:
    """Normalization used for exact-ish comparisons (key facts, cache keys)."""
    return " ".join(tokenize_plain(text))


def tokenize_plain(text: str) -> list[str]:
    """Lowercase alphanumeric tokens without the snake_case expansion."""
    return re.findall(r"[a-z0-9]+", text.lower())


def unique(items: Iterable[str]) -> list[str]:
    """Order-preserving de-duplication."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


@dataclass(frozen=True)
class TermStats:
    """Document frequencies over a corpus, for IDF weighting ("how informative is this word?")."""

    df: dict[str, int]
    n_docs: int

    @classmethod
    def from_texts(cls, texts: Iterable[str]) -> TermStats:
        df: Counter[str] = Counter()
        n = 0
        for text in texts:
            df.update(set(content_terms(text)))
            n += 1
        return cls(dict(df), n)

    def idf(self, term: str) -> float:
        # Smoothed IDF: a word in every document scores ~0, a word in no document scores highest.
        return math.log((self.n_docs + 1) / (self.df.get(term, 0) + 0.5))
