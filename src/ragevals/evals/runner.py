"""Run one pipeline config over the golden set and compute every metric."""

from __future__ import annotations

from dataclasses import asdict

from ragevals.evals.dataset import GoldenItem
from ragevals.evals.judge import Judge
from ragevals.evals.metrics import (
    evidence_hit,
    hit_at_k,
    key_fact_recall,
    mean,
    recall_at_k,
    reciprocal_rank,
    token_f1,
)
from ragevals.pipeline import RagPipeline


def evaluate_item(pipeline: RagPipeline, item: GoldenItem, judge: Judge) -> dict:
    answer = pipeline.answer(item.question)
    k = pipeline.config.k
    retrieved_sources = [c.source for c in answer.retrieved]
    row: dict = {
        "id": item.id,
        "type": item.type,
        "question": item.question,
        "answer": answer.answer,
        "refused": answer.refused,
        "should_refuse": item.should_refuse,
        "refusal_correct": answer.refused == item.should_refuse,
        "retrieved": [f"{c.source} > {c.heading}" for c in answer.retrieved],
        "expected_sources": item.expected_sources,
        "usage": answer.usage.to_dict(),
    }
    if item.should_refuse:
        return row

    if answer.refused:
        correctness, reason, judge_usage = 0.0, "refused an answerable question", None
    else:
        verdict = judge.grade(item.question, item.expected_answer, answer.answer, item.key_facts)
        correctness, reason, judge_usage = verdict.score, verdict.reason, verdict.usage
    row.update(
        {
            f"hit@{k}": hit_at_k(retrieved_sources, item.expected_sources, k),
            f"recall@{k}": recall_at_k(retrieved_sources, item.expected_sources, k),
            "rr": reciprocal_rank(retrieved_sources, item.expected_sources),
            f"evidence@{k}": evidence_hit(
                [(c.source, c.content) for c in answer.retrieved],
                item.expected_sources,
                item.key_facts,
            ),
            "key_fact_recall": 0.0
            if answer.refused
            else key_fact_recall(answer.answer, item.key_facts),
            "token_f1": 0.0 if answer.refused else token_f1(answer.answer, item.expected_answer),
            "correctness": correctness,
            "judge_reason": reason,
        }
    )
    if judge_usage and judge_usage.model != "none":
        row["judge_usage"] = judge_usage.to_dict()
    return row


def fraction(flags: list[bool]) -> str:
    return f"{sum(flags)}/{len(flags)}"


def summarize(rows: list[dict], k: int) -> dict:
    answerable = [r for r in rows if not r["should_refuse"]]
    unanswerable = [r for r in rows if r["should_refuse"]]

    def block(subset: list[dict]) -> dict:
        return {
            "n": len(subset),
            f"hit_rate@{k}": round(mean([r[f"hit@{k}"] for r in subset]), 4),
            f"recall@{k}": round(mean([r[f"recall@{k}"] for r in subset]), 4),
            "mrr": round(mean([r["rr"] for r in subset]), 4),
            f"evidence@{k}": round(mean([r[f"evidence@{k}"] for r in subset]), 4),
            "correctness": round(mean([r["correctness"] for r in subset]), 4),
            "key_fact_recall": round(mean([r["key_fact_recall"] for r in subset]), 4),
            "token_f1": round(mean([r["token_f1"] for r in subset]), 4),
        }

    costs = [r["usage"]["cost_usd"] for r in rows] + [
        r["judge_usage"]["cost_usd"] for r in rows if "judge_usage" in r
    ]
    return {
        "n": len(rows),
        "answerable": block(answerable),
        "by_type": {
            t: block([r for r in answerable if r["type"] == t])
            for t in ("single", "multi_hop")
            if any(r["type"] == t for r in answerable)
        },
        "refusal": {
            "accuracy": round(mean([float(r["refusal_correct"]) for r in rows]), 4),
            "unanswerable_refused": fraction([r["refused"] for r in unanswerable]),
            "answerable_refused": fraction([r["refused"] for r in answerable]),
        },
        "cost_usd": round(sum(costs), 6),
    }


def run_eval(pipeline: RagPipeline, items: list[GoldenItem], judge: Judge, embedder: str) -> dict:
    rows = [evaluate_item(pipeline, item, judge) for item in items]
    return {
        "config": asdict(pipeline.config),
        "embedder": embedder,
        "generator": pipeline.generator.name,
        "judge": judge.name,
        "k": pipeline.config.k,
        "summary": summarize(rows, pipeline.config.k),
        "items": rows,
    }
