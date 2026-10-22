"""Answer-correctness judges.

* ``OfflineJudge``   correctness = key-fact recall. Deterministic and free; used in CI.
* ``AnthropicJudge`` LLM-as-judge with the fast model (``LLM_FAST_MODEL``, default
                     ``claude-haiku-5-5``). It reads the question, the reference answer and the
                     candidate, and returns a 0 / 0.5 / 1 grade with a one-line reason.

LLM judges have their own failure modes (leniency, position bias, preferring long answers), so a
judge is itself something you evaluate: spot-check its grades against your own on ~20 items
before trusting a dashboard built on it. See LEARNING.md.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Protocol

from ragevals.llm import Usage, llm_provider


@dataclass
class Verdict:
    score: float  # 0..1
    reason: str
    usage: Usage = field(default_factory=lambda: Usage(model="none"))


class Judge(Protocol):
    name: str

    def grade(
        self, question: str, reference: str, answer: str, key_facts: list[str]
    ) -> Verdict: ...


class OfflineJudge:
    name = "offline:key-fact-recall"

    def grade(self, question: str, reference: str, answer: str, key_facts: list[str]) -> Verdict:
        from ragevals.evals.metrics import contains_fact

        found = [f for f in key_facts if contains_fact(answer, f)]
        missing = [f for f in key_facts if f not in found]
        score = len(found) / len(key_facts) if key_facts else 0.0
        reason = f"found {len(found)}/{len(key_facts)} key facts"
        if missing:
            reason += f"; missing: {', '.join(missing)}"
        return Verdict(score, reason)


JUDGE_PROMPT = """You are grading an answer produced by a documentation Q&A system.

Question:
{question}

Reference answer (written by a human from the docs):
{reference}

Key facts a complete answer should contain:
{facts}

Candidate answer:
{answer}

Grade the candidate ONLY on factual agreement with the reference:
- 1   = correct and covers the key facts (wording may differ; extra correct detail is fine)
- 0.5 = partially correct: some key facts present, nothing contradicts the reference
- 0   = wrong, contradicts the reference, or does not answer (including refusing)

Reply with JSON only, no prose: {{"score": <0|0.5|1>, "reason": "<one short sentence>"}}"""


class AnthropicJudge:
    def __init__(self, model: str | None = None) -> None:
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("LLM_FAST_MODEL", "claude-haiku-5-5")
        self.name = f"anthropic:{self.model}"

    def grade(self, question: str, reference: str, answer: str, key_facts: list[str]) -> Verdict:
        prompt = JUDGE_PROMPT.format(
            question=question,
            reference=reference,
            facts="\n".join(f"- {f}" for f in key_facts) or "- (none listed)",
            answer=answer,
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = Usage(self.model, response.usage.input_tokens, response.usage.output_tokens)
        return parse_verdict(text, usage)


def parse_verdict(text: str, usage: Usage | None = None) -> Verdict:
    """Pull the first JSON object out of the judge's reply; unparseable -> score 0."""
    usage = usage or Usage(model="none")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            score = min(1.0, max(0.0, float(data.get("score", 0))))
            return Verdict(score, str(data.get("reason", "")), usage)
        except (ValueError, TypeError):
            pass
    return Verdict(0.0, f"unparseable judge output: {text[:120]!r}", usage)


def get_judge(kind: str = "auto") -> Judge:
    """``auto`` uses the LLM judge when the Anthropic provider is active, else the offline one."""
    if kind == "auto":
        kind = "anthropic" if llm_provider() == "anthropic" else "offline"
    if kind == "offline":
        return OfflineJudge()
    if kind == "anthropic":
        return AnthropicJudge()
    raise ValueError(f"Unknown judge {kind!r} (expected auto, offline or anthropic)")
