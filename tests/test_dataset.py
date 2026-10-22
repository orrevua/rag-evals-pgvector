from collections import Counter

from ragevals.corpus import load_corpus
from ragevals.evals.dataset import load_golden
from ragevals.evals.metrics import contains_fact
from ragevals.settings import get_settings


def test_golden_set_shape():
    items = load_golden(get_settings().golden_path)
    assert len(items) == 40
    counts = Counter(i.type for i in items)
    assert counts["multi_hop"] >= 5 and counts["unanswerable"] >= 5
    assert all(len(i.expected_sources) >= 2 for i in items if i.type == "multi_hop")


def test_golden_sources_exist_and_key_facts_are_in_them():
    """Guards against typos: every key fact must literally appear in one of its source pages."""
    settings = get_settings()
    docs = {d.source: d.text for d in load_corpus(settings.corpus_dir)}
    for item in load_golden(settings.golden_path):
        for source in item.expected_sources:
            assert source in docs, f"{item.id}: unknown source {source}"
        for fact in item.key_facts:
            assert any(contains_fact(docs[s], fact) for s in item.expected_sources), (
                f"{item.id}: key fact {fact!r} not found in {item.expected_sources}"
            )
