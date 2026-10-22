"""Tiny text utilities shared by the hashing embedder, the rerankers, the fake LLM and the metrics.

Everything here is deliberately simple and dependency-free so you can read it in one sitting.
Real systems would use a proper tokenizer (e.g. the embedding model's own) and a stemmer
(e.g. Snowball). The point is to make the offline pipeline *deterministic* and *plausible*.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

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


def stem(token: str) -> str:
    """A very light suffix stripper ("parameters" -> "parameter", "validating" -> "validat").

    It only needs to be *consistent*: queries and documents go through the same function.
    """
    if len(token) <= 4 or "_" in token or token.isdigit():
        return token
    for suffix in ("ations", "ation", "ings", "ing", "ies", "ers", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            if suffix == "ies":
                return token[: -len(suffix)] + "y"
            return token[: -len(suffix)]
    return token


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
