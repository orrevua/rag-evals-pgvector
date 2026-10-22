"""Write eval reports: ``reports/<config>.json`` (all details) and ``.md`` (summary)."""

from __future__ import annotations

import json
from pathlib import Path


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict) -> str:
    s = report["summary"]
    k = report["k"]
    a = s["answerable"]
    cfg = report["config"]
    lines = [
        f"# Eval report: `{cfg['name']}`",
        "",
        f"{cfg['description']}",
        "",
        f"- Embedder: `{report['embedder']}`",
        f"- Generator: `{report['generator']}`",
        f"- Judge: `{report['judge']}`",
        f"- Questions: {s['n']} ({a['n']} answerable, {s['n'] - a['n']} unanswerable)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Retrieval hit rate@{k} | {pct(a[f'hit_rate@{k}'])} |",
        f"| Retrieval recall@{k} | {pct(a[f'recall@{k}'])} |",
        f"| MRR | {a['mrr']:.3f} |",
        f"| Evidence@{k} (answer passage retrieved) | {pct(a[f'evidence@{k}'])} |",
        f"| Answer correctness | {pct(a['correctness'])} |",
        f"| Key-fact recall | {pct(a['key_fact_recall'])} |",
        f"| Token F1 | {pct(a['token_f1'])} |",
        f"| Refusal accuracy | {pct(s['refusal']['accuracy'])} |",
        f"| Unanswerable refused | {s['refusal']['unanswerable_refused']} |",
        f"| Answerable wrongly refused | {s['refusal']['answerable_refused']} |",
        f"| LLM cost | ${s['cost_usd']:.4f} |",
        "",
        "## By question type",
        "",
        f"| Type | n | hit@{k} | recall@{k} | MRR | evidence@{k} | correctness |",
        "|---|---|---|---|---|---|---|",
    ]
    for kind, b in s["by_type"].items():
        lines.append(
            f"| {kind} | {b['n']} | {pct(b[f'hit_rate@{k}'])} | {pct(b[f'recall@{k}'])} "
            f"| {b['mrr']:.3f} | {pct(b[f'evidence@{k}'])} | {pct(b['correctness'])} |"
        )
    lines += [
        "",
        "## Per question",
        "",
        f"| id | type | hit@{k} | RR | correctness | refusal ok | first retrieved |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in report["items"]:
        first = r["retrieved"][0] if r["retrieved"] else "-"
        if r["should_refuse"]:
            lines.append(
                f"| {r['id']} | {r['type']} | - | - | - | "
                f"{'yes' if r['refusal_correct'] else 'NO'} | {first} |"
            )
        else:
            lines.append(
                f"| {r['id']} | {r['type']} | {r[f'hit@{k}']:.0f} | {r['rr']:.2f} "
                f"| {r['correctness']:.2f} | {'yes' if r['refusal_correct'] else 'NO'} | {first} |"
            )
    return "\n".join(lines) + "\n"


def write_report(report: dict, reports_dir: Path) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    name = report["config"]["name"]
    json_path = reports_dir / f"{name}.json"
    md_path = reports_dir / f"{name}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path
