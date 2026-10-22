from conftest import make_chunk

from ragevals.configs import get_config
from ragevals.evals.dataset import GoldenItem
from ragevals.evals.judge import OfflineJudge
from ragevals.evals.runner import run_eval
from ragevals.llm import ExtractiveGenerator
from ragevals.pipeline import RagPipeline

ITEMS = [
    GoldenItem(
        id="s01",
        type="single",
        question="What are the default values of skip and limit?",
        expected_answer="skip defaults to 0 and limit to 10",
        expected_sources=["query-params.md"],
        key_facts=["skip=0", "limit=10"],
    ),
    GoldenItem(
        id="u01",
        type="unanswerable",
        question="How do I deploy to AWS Lambda with Mangum?",
        expected_answer="Refuse",
        should_refuse=True,
    ),
]


class StubRetriever:
    def retrieve(self, question, k):
        return [
            make_chunk("cors.md", "Wildcards", "Wildcards allow all origins.", 0.5),
            make_chunk(
                "query-params.md",
                "Defaults",
                "In the example above they have default values of `skip=0` and `limit=10`.",
                0.4,
            ),
        ]


def test_run_eval_end_to_end_with_stubs():
    pipeline = RagPipeline(get_config("baseline"), StubRetriever(), ExtractiveGenerator())
    report = run_eval(pipeline, ITEMS, OfflineJudge(), embedder="stub")
    summary = report["summary"]
    assert summary["answerable"]["hit_rate@5"] == 1.0
    assert summary["answerable"]["mrr"] == 0.5
    assert summary["answerable"]["evidence@5"] == 1.0
    assert summary["answerable"]["correctness"] == 1.0
    assert summary["refusal"]["accuracy"] == 1.0
    assert summary["refusal"]["unanswerable_refused"] == "1/1"
