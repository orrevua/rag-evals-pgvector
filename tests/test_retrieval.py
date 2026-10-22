from conftest import make_chunk

from ragevals.rerank import LexicalReranker, parse_ranking
from ragevals.retrieval import RerankingRetriever, reciprocal_rank_fusion
from ragevals.store import RetrievedChunk


def chunk(key: str, score: float = 0.0) -> RetrievedChunk:
    return RetrievedChunk(key, key.split("#")[0], "h", "c", score)


def test_rrf_rewards_agreement_between_rankings():
    dense = [chunk("a#0"), chunk("b#0"), chunk("c#0")]
    sparse = [chunk("c#0"), chunk("d#0"), chunk("a#0")]
    fused = reciprocal_rank_fusion([dense, sparse], k=3)
    assert [c.chunk_key for c in fused][:2] == ["a#0", "c#0"]
    assert fused[0].score == round(1 / 61 + 1 / 63, 6)


def test_rrf_handles_empty_lists():
    assert reciprocal_rank_fusion([[], []], k=5) == []


def test_lexical_reranker_prefers_matching_heading_and_terms():
    chunks = [
        make_chunk("cors.md", "Wildcards", "Origins and credentials.", 0.9),
        make_chunk("status.md", "Response Status Code", "Use status_code=201 for Created.", 0.1),
    ]
    reranked = LexicalReranker().rerank("Which response status code means created?", chunks)
    assert reranked[0].source == "status.md"


class StubBase:
    def __init__(self):
        self.asked_k = None

    def retrieve(self, question, k):
        self.asked_k = k
        return [chunk(f"doc{i}.md#0", 1 - i / 10) for i in range(k)]


class ReverseReranker:
    name = "reverse"

    def rerank(self, question, chunks):
        return list(reversed(chunks))


def test_reranking_retriever_fetches_candidates_then_cuts_to_k():
    base = StubBase()
    out = RerankingRetriever(base, ReverseReranker(), candidates=20).retrieve("q", k=5)
    assert base.asked_k == 20
    assert [c.chunk_key for c in out] == [f"doc{i}.md#0" for i in range(19, 14, -1)]


def test_parse_ranking_fills_missing_and_ignores_garbage():
    assert parse_ranking("Ranking: [3, 1]", 4) == [2, 0, 1, 3]
    assert parse_ranking("no idea", 3) == [0, 1, 2]
