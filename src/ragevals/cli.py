"""Command line: ``ragevals init-db | ingest | ask``."""

from __future__ import annotations

import json
from contextlib import contextmanager

import typer

from ragevals.configs import CONFIGS, get_config
from ragevals.db import ensure_database, make_pool, migrate
from ragevals.embeddings import get_embedder
from ragevals.ingest import ingest as run_ingest
from ragevals.llm import get_generator
from ragevals.pipeline import build_pipeline
from ragevals.settings import get_settings
from ragevals.store import PgVectorStore

app = typer.Typer(help="RAG over the FastAPI tutorial, with evals.", no_args_is_help=True)


@contextmanager
def open_store():
    pool = make_pool(get_settings().database_url)
    try:
        yield PgVectorStore(pool)
    finally:
        pool.close()


def resolve_configs(name: str) -> list:
    return list(CONFIGS.values()) if name == "all" else [get_config(name)]


@app.command("init-db")
def init_db() -> None:
    """Create the database (if missing) and apply pending SQL migrations."""
    url = get_settings().database_url
    if ensure_database(url):
        typer.echo("created database")
    applied = migrate(url)
    typer.echo(f"applied migrations: {', '.join(applied) or 'none (up to date)'}")


@app.command()
def ingest(
    config: str = typer.Option("all", help="Config name, or 'all' for every config"),
) -> None:
    """Chunk + embed the corpus into the collection(s) the config(s) need."""
    settings = get_settings()
    embedder = get_embedder()
    with open_store() as store:
        for result in run_ingest(store, embedder, resolve_configs(config), settings.corpus_dir):
            typer.echo(
                f"{result.collection}: {result.chunks} chunks from {result.documents} documents"
            )


@app.command()
def ask(
    question: str,
    config: str = typer.Option("baseline", help="Pipeline config name"),
    show_context: bool = typer.Option(False, help="Also print the retrieved chunks"),
) -> None:
    """Answer one question from the command line."""
    with open_store() as store:
        pipeline = build_pipeline(get_config(config), store, get_embedder(), get_generator())
        answer = pipeline.answer(question)
    typer.echo(json.dumps(answer.to_dict(include_retrieved=show_context), indent=2))


if __name__ == "__main__":
    app()
