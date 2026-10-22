"""The CI eval gate: fail the build if a metric drops below its committed threshold.

``evals/gate.json`` holds minimum values per config, e.g.::

    {"thresholds": {"combined": {"hit_rate@5": 0.95, "correctness": 0.5}}}

Metric names are looked up in the report summary: first under ``answerable``, then
``refusal`` (``refusal_accuracy`` maps to ``refusal.accuracy``). Thresholds are set a little
below the current numbers so that noise does not fail the build but a real regression does.
Raising them is a deliberate, reviewed change to a committed file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GateResult:
    config: str
    metric: str
    value: float | None
    threshold: float

    @property
    def passed(self) -> bool:
        return self.value is not None and self.value >= self.threshold


def metric_value(summary: dict, metric: str) -> float | None:
    if metric == "refusal_accuracy":
        return summary["refusal"]["accuracy"]
    return summary["answerable"].get(metric)


def check_gate(gate_path: Path, reports_dir: Path) -> list[GateResult]:
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    results: list[GateResult] = []
    for config, thresholds in gate["thresholds"].items():
        report_path = reports_dir / f"{config}.json"
        summary = (
            json.loads(report_path.read_text(encoding="utf-8"))["summary"]
            if report_path.exists()
            else None
        )
        for metric, threshold in thresholds.items():
            value = metric_value(summary, metric) if summary else None
            results.append(GateResult(config, metric, value, float(threshold)))
    return results
