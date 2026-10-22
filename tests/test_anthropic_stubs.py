"""The Anthropic code paths, exercised with stub clients (no network, no API key)."""

from contextlib import contextmanager
from types import SimpleNamespace

from conftest import make_chunk

from ragevals.evals.judge import AnthropicJudge
from ragevals.llm import REFUSAL, AnthropicGenerator, Generation
from ragevals.rerank import LLMReranker

CONTEXTS = [make_chunk("a.md", "A", "alpha"), make_chunk("b.md", "B", "beta")]


def reply(text: str):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=1000, output_tokens=100),
    )


class StubMessages:
    def __init__(self, text: str):
        self.text = text
        self.kwargs: dict = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        return reply(self.text)

    @contextmanager
    def stream(self, **kwargs):
        self.kwargs = kwargs
        words = self.text.split(" ")
        yield SimpleNamespace(
            text_stream=iter(w + " " for w in words),
            get_final_message=lambda: reply(self.text),
        )


def stub(cls, text: str, **attrs):
    obj = cls.__new__(cls)  # skip __init__: no real client, no key needed
    obj.client = SimpleNamespace(messages=StubMessages(text))
    for key, value in attrs.items():
        setattr(obj, key, value)
    return obj


def test_generator_parses_citations_usage_and_cost():
    gen = stub(
        AnthropicGenerator,
        "Use beta [2], not alpha [1][7].",
        model="claude-sonnet-5-5",
        max_tokens=100,
        name="anthropic:claude-sonnet-5-5",
    )
    out = gen.generate("q?", CONTEXTS)
    assert out.cited == [2, 1] and not out.refused
    assert out.usage.cost_usd == (1000 * 2.0 + 100 * 10.0) / 1_000_000
    sent = gen.client.messages.kwargs
    assert "[2] (file: b.md | section: B)" in sent["messages"][0]["content"]
    assert "temperature" not in sent  # sampling params are rejected by current models


def test_generator_detects_refusal_and_streams():
    gen = stub(AnthropicGenerator, REFUSAL, model="m", max_tokens=100, name="anthropic:m")
    *deltas, final = list(gen.stream("q?", CONTEXTS))
    assert isinstance(final, Generation) and final.refused
    assert "".join(deltas).strip() == REFUSAL


def test_judge_and_llm_reranker():
    judge = stub(AnthropicJudge, '{"score": 0.5, "reason": "partial"}', model="claude-haiku-5-5")
    verdict = judge.grade("q", "ref", "ans", ["x"])
    assert verdict.score == 0.5 and verdict.usage.model == "claude-haiku-5-5"

    reranker = stub(LLMReranker, "[2, 1]", model="m", name="llm:m")
    assert [c.source for c in reranker.rerank("q", CONTEXTS)] == ["b.md", "a.md"]
