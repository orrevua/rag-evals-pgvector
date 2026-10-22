"""The golden dataset: hand-written questions with expected answers and sources."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

TYPES = ("single", "multi_hop", "unanswerable")


@dataclass(frozen=True)
class GoldenItem:
    id: str
    type: str  # "single" | "multi_hop" | "unanswerable"
    question: str
    expected_answer: str
    expected_sources: list[str] = field(default_factory=list)  # corpus-relative file paths
    key_facts: list[str] = field(default_factory=list)  # short phrases a correct answer contains
    should_refuse: bool = False


def load_golden(path: Path) -> list[GoldenItem]:
    items: list[GoldenItem] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = GoldenItem(**json.loads(line))
        if item.type not in TYPES:
            raise ValueError(f"{path}:{line_no}: unknown type {item.type!r}")
        if item.should_refuse != (item.type == "unanswerable"):
            raise ValueError(f"{path}:{line_no}: should_refuse must match type")
        if not item.should_refuse and not item.expected_sources:
            raise ValueError(f"{path}:{line_no}: answerable items need expected_sources")
        items.append(item)
    ids = [i.id for i in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate ids")
    return items
