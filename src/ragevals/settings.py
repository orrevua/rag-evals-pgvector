"""Configuration from environment variables (see ``.env.example``)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _path(var: str, default: str) -> Path:
    value = Path(os.getenv(var, default))
    return value if value.is_absolute() else PROJECT_ROOT / value


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/p1_rag"
        )
    )
    corpus_dir: Path = field(
        default_factory=lambda: _path("CORPUS_DIR", "data/corpus/fastapi-tutorial")
    )
    golden_path: Path = field(default_factory=lambda: _path("GOLDEN_PATH", "evals/golden.jsonl"))
    reports_dir: Path = field(default_factory=lambda: _path("REPORTS_DIR", "reports"))


def get_settings() -> Settings:
    return Settings()
