"""Shared fixtures. Postgres tests use DATABASE_URL and skip cleanly when it is unreachable."""

from __future__ import annotations

import os
import uuid

import pytest

from ragevals.store import RetrievedChunk

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/p1_rag")


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never call a real API from the test suite, even if a key happens to be set."""
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("EMBEDDER", "hash")


@pytest.fixture(scope="session")
def pg_pool():
    from ragevals.db import can_connect, ensure_database, make_pool, migrate

    try:
        if not can_connect(DATABASE_URL):
            ensure_database(DATABASE_URL)
    except Exception as exc:  # server down, auth failure, ...
        pytest.skip(f"Postgres unreachable at DATABASE_URL: {exc}")
    if not can_connect(DATABASE_URL):
        pytest.skip("Postgres unreachable at DATABASE_URL")
    migrate(DATABASE_URL)
    pool = make_pool(DATABASE_URL)
    yield pool
    pool.close()


@pytest.fixture
def collection_name() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


def make_chunk(source: str, heading: str, content: str, score: float = 1.0) -> RetrievedChunk:
    return RetrievedChunk(f"{source}#0", source, heading, content, score)
