"""Answer cache in Postgres.

RAG answers are expensive (an LLM call) and questions repeat, so caching the final response is
the cheapest latency and cost win there is. The cache key must include everything that changes
the answer: the normalised question, the pipeline config, the generator model and the embedder.
Re-ingesting the corpus clears the cache (see ``ingest``), because the context changed.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from ragevals.text import normalize


def cache_key(question: str, config: str, generator: str, embedder: str) -> str:
    """ "What is X?" and "what is x" share a key; different configs/models never do."""
    material = "\x1f".join([normalize(question), config, generator, embedder])
    return hashlib.sha256(material.encode()).hexdigest()


class AnswerCache(Protocol):
    def get(self, key: str) -> dict | None: ...

    def put(self, key: str, question: str, config: str, response: dict) -> None: ...


class PgAnswerCache:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def get(self, key: str) -> dict | None:
        with self.pool.connection() as conn:
            row = conn.execute(
                "UPDATE answer_cache SET hits = hits + 1, last_hit_at = now()"
                " WHERE cache_key = %s RETURNING response",
                (key,),
            ).fetchone()
        return row[0] if row else None

    def put(self, key: str, question: str, config: str, response: dict) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                "INSERT INTO answer_cache (cache_key, question, config, response)"
                " VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (cache_key) DO UPDATE SET response = EXCLUDED.response,"
                " created_at = now()",
                (key, question, config, Jsonb(response)),
            )

    def clear(self) -> int:
        with self.pool.connection() as conn:
            return conn.execute("DELETE FROM answer_cache").rowcount


class MemoryAnswerCache:
    """In-process cache with the same interface; used by tests."""

    def __init__(self) -> None:
        self.data: dict[str, dict] = {}

    def get(self, key: str) -> dict | None:
        return self.data.get(key)

    def put(self, key: str, question: str, config: str, response: dict) -> None:
        self.data[key] = response
