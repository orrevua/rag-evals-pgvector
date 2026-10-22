import json

from conftest import make_chunk
from fastapi.testclient import TestClient

from ragevals.api import Services, create_app
from ragevals.cache import MemoryAnswerCache
from ragevals.configs import get_config
from ragevals.llm import ExtractiveGenerator
from ragevals.observability import MemoryRequestLog
from ragevals.pipeline import RagPipeline

QUESTION = {"question": "default values of skip and limit?"}


class StubRetriever:
    def __init__(self):
        self.calls = 0

    def retrieve(self, question: str, k: int):
        self.calls += 1
        return [
            make_chunk(
                "query-params.md",
                "Defaults",
                "In the example above they have default values of `skip=0` and `limit=10`.",
                0.9,
            )
        ][:k]


def make_app(with_cache: bool = True):
    retriever = StubRetriever()
    pipeline = RagPipeline(get_config("baseline"), retriever, ExtractiveGenerator())
    log = MemoryRequestLog()
    services = Services(
        pipeline_for=lambda name: pipeline,
        cache=MemoryAnswerCache() if with_cache else None,
        request_log=log,
        embedder_name="stub",
    )
    return TestClient(create_app(services)), retriever, log


def test_ask_returns_answer_with_sources_and_headers():
    client, _, _ = make_app()
    with client:
        response = client.post("/ask", json=QUESTION)
    assert response.status_code == 200
    body = response.json()
    assert "skip=0" in body["answer"]
    assert body["cached"] is False
    assert body["sources"][0] == {
        "source": "query-params.md",
        "heading": "Defaults",
        "chunk_key": "query-params.md#0",
        "score": 0.9,
    }
    assert body["usage"]["model"] == "fake"
    assert response.headers["x-request-id"]
    assert float(response.headers["x-process-time"]) >= 0


def test_second_identical_question_is_served_from_cache():
    client, retriever, log = make_app()
    with client:
        first = client.post("/ask", json=QUESTION).json()
        second = client.post("/ask", json={"question": "Default values of SKIP and limit"}).json()
    assert retriever.calls == 1  # normalised question -> same cache key -> no second retrieval
    assert second["cached"] is True and second["answer"] == first["answer"]
    assert [r.cached for r in log.records] == [False, True]
    assert log.records[1].cost_usd == 0 and log.records[1].input_tokens == 0


def test_use_cache_false_bypasses_cache():
    client, retriever, _ = make_app()
    with client:
        client.post("/ask", json=QUESTION)
        client.post("/ask", json={**QUESTION, "use_cache": False})
    assert retriever.calls == 2


def test_request_log_records_tokens_and_latency():
    client, _, log = make_app()
    with client:
        client.post("/ask", json=QUESTION, headers={"X-Request-ID": "abc123"})
    rec = log.records[0]
    assert rec.request_id == "abc123"
    assert rec.endpoint == "/ask" and rec.config == "baseline"
    assert rec.input_tokens > 0 and rec.output_tokens > 0
    assert rec.total_ms > 0 and rec.retrieval_ms is not None


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def test_stream_sends_tokens_then_done():
    client, _, log = make_app()
    with client:
        response = client.post("/ask/stream", json=QUESTION)
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    kinds = [kind for kind, _ in events]
    assert kinds[-1] == "done" and set(kinds[:-1]) == {"token"}
    done = events[-1][1]
    assert "".join(data["text"] for kind, data in events[:-1]) == done["answer"]
    assert done["sources"][0]["source"] == "query-params.md"
    assert log.records[0].endpoint == "/ask/stream"


def test_unknown_config_is_422():
    client, _, _ = make_app()
    with client:
        assert client.post("/ask", json={**QUESTION, "config": "nope"}).status_code == 422
        assert client.post("/ask/stream", json={**QUESTION, "config": "nope"}).status_code == 422


def test_question_is_validated():
    client, _, _ = make_app(with_cache=False)
    with client:
        assert client.post("/ask", json={"question": ""}).status_code == 422
