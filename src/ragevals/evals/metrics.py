"""Metrics. Pure functions over plain data, so they are trivial to unit test.

Retrieval (is the right page in the top k?)
    hit@k      1 if any expected source is among the top-k retrieved sources, else 0.
    recall@k   fraction of the expected sources found in the top k (matters for multi-hop).
    MRR        1 / rank of the first relevant chunk (0 if none). Rewards ranking it *first*.
    evidence@k 1 if a top-k chunk from an expected source actually contains a key fact.
               File-level metrics saturate quickly on a small corpus (the right *page* is easy
               to find); this one asks whether the right *passage* made it into the prompt.

Answer (is the answer right?)
    key-fact recall  fraction of the item's key facts that appear in the answer (after
                     normalisation). Cheap, deterministic, surprisingly informative.
    token F1         SQuAD-style word overlap with the reference answer. Penalises verbosity
                     and paraphrase, so it is a weak signal on its own.
    LLM judge        (when an API key is available) a fast model grades the answer against the
                     reference. See ``judge.py``.

Refusal
    accuracy    did the system refuse exactly when it should have?
"""

from __future__ import annotations

import re
from collections import Counter

from ragevals.text import tokenize_plain

_CITATION_RE = re.compile(r"\[\d+\]")
_F1_IGNORE = frozenset({"a", "an", "the", "and", "or", "of", "to", "is", "it", "in"})


def hit_at_k(retrieved_sources: list[str], expected: list[str], k: int) -> float:
    return 1.0 if set(retrieved_sources[:k]) & set(expected) else 0.0


def recall_at_k(retrieved_sources: list[str], expected: list[str], k: int) -> float:
    if not expected:
        return 0.0
    return len(set(retrieved_sources[:k]) & set(expected)) / len(set(expected))


def reciprocal_rank(retrieved_sources: list[str], expected: list[str]) -> float:
    for rank, source in enumerate(retrieved_sources, start=1):
        if source in expected:
            return 1.0 / rank
    return 0.0


def evidence_hit(
    retrieved: list[tuple[str, str]], expected_sources: list[str], key_facts: list[str]
) -> float:
    """``retrieved`` is (source, content) pairs of the top-k chunks."""
    for source, content in retrieved:
        if source in expected_sources and any(contains_fact(content, f) for f in key_facts):
            return 1.0
    return 0.0


def _answer_tokens(text: str) -> list[str]:
    return [t for t in tokenize_plain(_CITATION_RE.sub(" ", text)) if t not in _F1_IGNORE]


def token_f1(prediction: str, reference: str) -> float:
    pred, ref = _answer_tokens(prediction), _answer_tokens(reference)
    if not pred or not ref:
        return 0.0
    common = sum((Counter(pred) & Counter(ref)).values())
    if common == 0:
        return 0.0
    precision, recall = common / len(pred), common / len(ref)
    return 2 * precision * recall / (precision + recall)


def contains_fact(answer: str, fact: str) -> bool:
    """Token-sequence containment: "use_cache=False" matches "Depends(f, use_cache=False)"."""
    haystack = " " + " ".join(tokenize_plain(_CITATION_RE.sub(" ", answer))) + " "
    needle = " " + " ".join(tokenize_plain(fact)) + " "
    return needle.strip() != "" and needle in haystack


def key_fact_recall(answer: str, facts: list[str]) -> float:
    if not facts:
        return 0.0
    return sum(contains_fact(answer, f) for f in facts) / len(facts)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
