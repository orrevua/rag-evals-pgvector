"""Structured logging and the ``request_log`` table.

Every API request produces one JSON log line (for your log pipeline: Loki, CloudWatch, ...) and
one ``request_log`` row (for SQL questions like "what did we spend yesterday, per config?").
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol

from psycopg_pool import ConnectionPool

logger = logging.getLogger("ragevals.requests")


class JsonFormatter(logging.Formatter):
    """One JSON object per line; extra fields via ``extra={"fields": {...}}``."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("ragevals")
    root.handlers[:] = [handler]
    root.setLevel(level)
    root.propagate = False


@dataclass
class RequestRecord:
    request_id: str
    endpoint: str
    config: str
    question: str
    cached: bool
    total_ms: float
    refused: bool | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    retrieval_ms: float | None = None
    generation_ms: float | None = None
    n_sources: int | None = None
    error: str | None = None


class RequestLog(Protocol):
    def record(self, rec: RequestRecord) -> None: ...


class PgRequestLog:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def record(self, rec: RequestRecord) -> None:
        logger.info("request", extra={"fields": asdict(rec)})
        data = asdict(rec)
        columns = ", ".join(data)
        placeholders = ", ".join(["%s"] * len(data))
        try:
            with self.pool.connection() as conn:
                conn.execute(
                    f"INSERT INTO request_log ({columns}) VALUES ({placeholders})",
                    list(data.values()),
                )
        except Exception:  # logging must never break a request
            logger.exception("failed to write request_log row")


class MemoryRequestLog:
    def __init__(self) -> None:
        self.records: list[RequestRecord] = []

    def record(self, rec: RequestRecord) -> None:
        logger.info("request", extra={"fields": asdict(rec)})
        self.records.append(rec)
