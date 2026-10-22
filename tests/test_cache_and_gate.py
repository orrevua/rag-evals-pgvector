import json

from ragevals.cache import cache_key
from ragevals.evals.gate import check_gate


def test_cache_key_normalises_question_but_not_config_or_model():
    base = cache_key("What is CORS?", "baseline", "fake", "hash512")
    assert base == cache_key("  what is cors ", "baseline", "fake", "hash512")
    assert base != cache_key("What is CORS?", "hybrid", "fake", "hash512")
    assert base != cache_key("What is CORS?", "baseline", "anthropic:x", "hash512")
    assert base != cache_key("What is CORS?", "baseline", "fake", "fastembed")


def test_gate_passes_and_fails(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    summary = {"answerable": {"hit_rate@5": 0.9, "mrr": 0.8}, "refusal": {"accuracy": 0.7}}
    (reports / "baseline.json").write_text(json.dumps({"summary": summary}))
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "thresholds": {
                    "baseline": {"hit_rate@5": 0.85, "mrr": 0.9, "refusal_accuracy": 0.7},
                    "missing": {"hit_rate@5": 0.5},
                }
            }
        )
    )
    results = {(r.config, r.metric): r.passed for r in check_gate(gate, reports)}
    assert results == {
        ("baseline", "hit_rate@5"): True,
        ("baseline", "mrr"): False,
        ("baseline", "refusal_accuracy"): True,
        ("missing", "hit_rate@5"): False,  # a missing report fails the gate, never passes it
    }
