from ragevals.evals.judge import OfflineJudge, get_judge, parse_verdict


def test_offline_judge_scores_key_facts():
    verdict = OfflineJudge().grade("q", "ref", "HS256 and pwdlib", ["HS256", "pwdlib", "Argon2"])
    assert round(verdict.score, 2) == 0.67
    assert "Argon2" in verdict.reason


def test_parse_verdict_extracts_json_and_clamps():
    assert parse_verdict('Sure! {"score": 0.5, "reason": "partial"}').score == 0.5
    assert parse_verdict('{"score": 7}').score == 1.0
    assert parse_verdict("no json here").score == 0.0


def test_auto_judge_is_offline_without_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    assert get_judge("auto").name.startswith("offline")
