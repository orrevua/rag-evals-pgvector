from conftest import make_chunk
from fastapi.testclient import TestClient

from ragevals.api import Services, create_app
from ragevals.configs import get_config
from ragevals.llm import ExtractiveGenerator
from ragevals.pipeline import RagPipeline


class StubRetriever:
    def retrieve(self, question: str, k: int):
        return [
            make_chunk(
                "query-params.md",
                "Defaults",
                "In the example above they have default values of `skip=0` and `limit=10`.",
                0.9,
            )
        ][:k]


def make_client() -> TestClient:
    pipeline = RagPipeline(get_config("baseline"), StubRetriever(), ExtractiveGenerator())
    return TestClient(create_app(Services(pipeline_for=lambda name: pipeline)))


def test_ask_returns_answer_with_sources():
    with make_client() as client:
        response = client.post("/ask", json={"question": "default values of skip and limit?"})
    assert response.status_code == 200
    body = response.json()
    assert "skip=0" in body["answer"]
    assert body["sources"][0] == {
        "source": "query-params.md",
        "heading": "Defaults",
        "chunk_key": "query-params.md#0",
        "score": 0.9,
    }
    assert body["usage"]["model"] == "fake"


def test_ask_unknown_config_is_404():
    with make_client() as client:
        response = client.post("/ask", json={"question": "anything here?", "config": "nope"})
    assert response.status_code == 404


def test_ask_validates_question():
    with make_client() as client:
        assert client.post("/ask", json={"question": ""}).status_code == 422
