"""Postgres plumbing: create the database, apply plain-SQL migrations, open a connection pool.

Migrations are numbered ``.sql`` files in ``ragevals/migrations``. Each one is applied once, in
order, inside a transaction, and recorded in ``schema_migrations``. That is all a migration tool
fundamentally does; Alembic/Flyway add autogeneration, downgrades and locking on top.
"""

from __future__ import annotations

from importlib import resources

import psycopg
from pgvector.psycopg import register_vector
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg_pool import ConnectionPool


def ensure_database(database_url: str) -> bool:
    """Create the target database if it does not exist. Returns True if it was created."""
    params = conninfo_to_dict(database_url)
    dbname = params.get("dbname", "postgres")
    admin_url = make_conninfo(database_url, dbname="postgres")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
        if exists:
            return False
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
        return True


def migration_files() -> list[tuple[str, str]]:
    """(version, sql) pairs sorted by file name."""
    folder = resources.files("ragevals") / "migrations"
    files = sorted(
        (entry for entry in folder.iterdir() if entry.name.endswith(".sql")),
        key=lambda e: e.name,
    )
    return [(entry.name.removesuffix(".sql"), entry.read_text(encoding="utf-8")) for entry in files]


def migrate(database_url: str) -> list[str]:
    """Apply pending migrations. Returns the versions applied in this call."""
    applied_now: list[str] = []
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        conn.commit()
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for version, statements in migration_files():
            if version in done:
                continue
            with conn.transaction():
                conn.execute(statements)  # psycopg sends multi-statement scripts as-is
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            applied_now.append(version)
    return applied_now


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)  # lets us pass numpy arrays / lists as pgvector values


def make_pool(database_url: str, *, min_size: int = 1, max_size: int = 5) -> ConnectionPool:
    pool = ConnectionPool(
        database_url, min_size=min_size, max_size=max_size, configure=_configure, open=False
    )
    pool.open(wait=True, timeout=10)
    return pool


def can_connect(database_url: str, timeout: int = 2) -> bool:
    try:
        with psycopg.connect(database_url, connect_timeout=timeout):
            return True
    except psycopg.OperationalError:
        return False
