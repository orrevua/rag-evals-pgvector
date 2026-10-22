import pytest

from ragevals.evals.metrics import (
    contains_fact,
    evidence_hit,
    hit_at_k,
    key_fact_recall,
    recall_at_k,
    reciprocal_rank,
    token_f1,
)

RETRIEVED = ["a.md", "b.md", "c.md", "a.md", "d.md"]


def test_hit_at_k():
    assert hit_at_k(RETRIEVED, ["c.md"], k=3) == 1.0
    assert hit_at_k(RETRIEVED, ["d.md"], k=3) == 0.0


def test_recall_at_k_for_multi_hop():
    assert recall_at_k(RETRIEVED, ["a.md", "d.md"], k=3) == 0.5
    assert recall_at_k(RETRIEVED, ["a.md", "d.md"], k=5) == 1.0


def test_reciprocal_rank():
    assert reciprocal_rank(RETRIEVED, ["b.md"]) == 0.5
    assert reciprocal_rank(RETRIEVED, ["z.md"]) == 0.0


def test_token_f1_ignores_citations_and_case():
    assert token_f1("Skip defaults to 0 [1]", "skip defaults to 0") == 1.0
    assert token_f1("", "anything") == 0.0
    assert 0 < token_f1("skip defaults to 0 and limit to 10", "skip defaults to 0") < 1


@pytest.mark.parametrize(
    ("answer", "fact", "expected"),
    [
        ("Use Depends(get_value, use_cache=False) [1]", "use_cache=False", True),
        ("default values of `skip=0` and `limit=10`.", "skip=0", True),
        ("the value skip=01", "skip=0", False),  # token boundaries, not substrings
        ("the cookies won't be sent", "cookies won't be sent", True),
    ],
)
def test_contains_fact(answer, fact, expected):
    assert contains_fact(answer, fact) is expected


def test_key_fact_recall():
    assert key_fact_recall("HS256 and Argon2", ["HS256", "pwdlib", "Argon2"]) == pytest.approx(
        2 / 3
    )
    assert key_fact_recall("anything", []) == 0.0


def test_evidence_hit_requires_expected_source_and_fact():
    retrieved = [("x.md", "skip=0 here"), ("a.md", "nothing useful")]
    assert evidence_hit(retrieved, ["a.md"], ["skip=0"]) == 0.0
    assert evidence_hit(retrieved + [("a.md", "skip=0")], ["a.md"], ["skip=0"]) == 1.0
