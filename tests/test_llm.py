from conftest import make_chunk

from ragevals.llm import REFUSAL, ExtractiveGenerator, Usage, parse_citations, split_sentences

CONTEXTS = [
    make_chunk(
        "query-params.md",
        "Defaults",
        "As query parameters are not a fixed part of a path, they can be optional and can have "
        "default values. In the example above they have default values of `skip=0` and `limit=10`.",
    ),
    make_chunk("cors.md", "Wildcards", "It's also possible to declare the list as a wildcard."),
]


def test_extractive_answer_quotes_and_cites():
    gen = ExtractiveGenerator().generate("What are the default values of skip and limit?", CONTEXTS)
    assert not gen.refused
    assert "skip=0" in gen.text and "[1]" in gen.text
    assert gen.cited == [1]


def test_extractive_refuses_off_topic_question():
    gen = ExtractiveGenerator().generate("How do I deploy to AWS Lambda with Mangum?", CONTEXTS)
    assert gen.refused and gen.text == REFUSAL and gen.cited == []


def test_stream_yields_text_then_generation():
    items = list(ExtractiveGenerator().stream("default values of skip and limit?", CONTEXTS))
    *deltas, final = items
    assert "".join(deltas) == final.text


def test_parse_citations_ignores_out_of_range_and_duplicates():
    assert parse_citations("a [2] b [1] c [2] d [9]", n_contexts=3) == [2, 1]


def test_split_sentences_handles_lists_and_code():
    text = "Intro sentence. Second One.\n\n* bullet item\n\n```python\nx = 1\n```"
    assert split_sentences(text) == ["Intro sentence.", "Second One.", "bullet item", "x = 1"]


def test_usage_cost():
    assert Usage("claude-haiku-5-5", 1_000_000, 0).cost_usd == 0.10
    assert Usage("fake", 10, 10).cost_usd == 0.0
