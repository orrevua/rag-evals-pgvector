"""The pgvector store: write chunks with their embeddings, read back the nearest ones.

All SQL lives in this file, so you can see exactly what hits the database.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from psycopg_pool import ConnectionPool

from ragevals.chunking import Chunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_key: str
    source: str
    heading: str
    content: str
    score: float  # higher is better; meaning depends on the retriever (cosine, ts_rank, RRF...)


class PgVectorStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    # --- writes ---------------------------------------------------------------------------------

    def replace_collection(
        self,
        collection: str,
        *,
        chunker: str,
        embedder: str,
        dim: int,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> int:
        """Atomically replace a collection's chunks (delete + insert in one transaction).

        Readers see either the old or the new collection, never a half-written one.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        with self.pool.connection() as conn, conn.transaction():
            conn.execute(
                "INSERT INTO collections (name, chunker, embedder, dim) VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (name) DO UPDATE SET chunker = EXCLUDED.chunker,"
                " embedder = EXCLUDED.embedder, dim = EXCLUDED.dim, created_at = now()",
                (collection, chunker, embedder, dim),
            )
            conn.execute("DELETE FROM chunks WHERE collection = %s", (collection,))
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO chunks"
                    " (collection, chunk_key, source, heading, content, embedding)"
                    " VALUES (%s, %s, %s, %s, %s, %s)",
                    [
                        (collection, c.chunk_key, c.source, c.heading, c.content, np.asarray(e))
                        for c, e in zip(chunks, embeddings, strict=True)
                    ],
                )
        return len(chunks)

    def drop_collection(self, collection: str) -> None:
        with self.pool.connection() as conn:
            conn.execute("DELETE FROM collections WHERE name = %s", (collection,))

    # --- reads ----------------------------------------------------------------------------------

    def count(self, collection: str) -> int:
        with self.pool.connection() as conn:
            row = conn.execute(
                "SELECT count(*) FROM chunks WHERE collection = %s", (collection,)
            ).fetchone()
        return int(row[0]) if row else 0

    def vector_search(
        self, collection: str, query_embedding: list[float], k: int
    ) -> list[RetrievedChunk]:
        """Exact nearest neighbours by cosine distance (``<=>``); score = cosine similarity."""
        with self.pool.connection() as conn:
            rows = conn.execute(
                "SELECT chunk_key, source, heading, content, 1 - (embedding <=> %s) AS score"
                " FROM chunks WHERE collection = %s"
                " ORDER BY embedding <=> %s, chunk_key LIMIT %s",
                (np.asarray(query_embedding), collection, np.asarray(query_embedding), k),
            ).fetchall()
        return [RetrievedChunk(*row) for row in rows]
