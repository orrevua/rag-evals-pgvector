"""Command line: ``ragevals init-db | ingest | ask | eval | eval-all | gate``."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import typer

from ragevals.cache import PgAnswerCache
from ragevals.configs import CONFIGS, get_config
from ragevals.corpus import corpus_stats
from ragevals.db import ensure_database, make_pool, migrate
from ragevals.embeddings import get_embedder
from ragevals.evals.dataset import load_golden
from ragevals.evals.gate import check_gate
from ragevals.evals.judge import get_judge
from ragevals.evals.report import render_markdown, render_results, write_report
from ragevals.evals.runner import run_eval
from ragevals.ingest import ingest as run_ingest
from ragevals.llm import get_generator
from ragevals.pipeline import build_pipeline
from ragevals.settings import PROJECT_ROOT, get_settings
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
        # The context changed, so cached answers may be stale.
        typer.echo(f"cleared {PgAnswerCache(store.pool).clear()} cached answers")


@app.command()
def ask(
    question: str,
    config: str = typer.Option("baseline", help="Pipeline config name"),
    show_context: bool = typer.Option(False, help="Also print the retrieved chunks"),
) -> None:
    """Answer one question from the command line."""
    settings = get_settings()
    with open_store() as store:
        pipeline = build_pipeline(
            get_config(config),
            store,
            get_embedder(),
            get_generator(),
            corpus_stats(settings.corpus_dir),
        )
        answer = pipeline.answer(question)
    typer.echo(json.dumps(answer.to_dict(include_retrieved=show_context), indent=2))


def run_and_write(config_name: str, judge_kind: str, limit: int | None) -> dict:
    settings = get_settings()
    items = load_golden(settings.golden_path)[:limit]
    embedder = get_embedder()
    with open_store() as store:
        config = get_config(config_name)
        pipeline = build_pipeline(
            config, store, embedder, get_generator(), corpus_stats(settings.corpus_dir)
        )
        report = run_eval(pipeline, items, get_judge(judge_kind), embedder.name)
    json_path, md_path = write_report(report, settings.reports_dir)
    typer.echo(f"wrote {json_path} and {md_path}")
    return report


@app.command("eval")
def eval_(
    config: str = typer.Option("baseline", help="Config name"),
    judge: str = typer.Option("auto", help="auto | offline | anthropic"),
    limit: int = typer.Option(None, help="Only the first N golden items (quick checks)"),
) -> None:
    """Evaluate one config on evals/golden.jsonl; writes reports/<config>.json and .md."""
    report = run_and_write(config, judge, limit)
    typer.echo(render_markdown(report).split("## By question type")[0])


@app.command("eval-all")
def eval_all(
    judge: str = typer.Option("auto", help="auto | offline | anthropic"),
) -> None:
    """Evaluate every config and write reports/RESULTS.md comparing them to the baseline."""
    reports = [run_and_write(name, judge, None) for name in CONFIGS]
    path = get_settings().reports_dir / "RESULTS.md"
    path.write_text(render_results(reports), encoding="utf-8")
    typer.echo(f"wrote {path}")
    typer.echo(path.read_text(encoding="utf-8"))


@app.command()
def gate(
    gate_file: str = typer.Option("evals/gate.json", help="Committed thresholds"),
) -> None:
    """Fail (exit 1) if any report metric is below its threshold in evals/gate.json."""
    settings = get_settings()
    path = Path(gate_file)
    results = check_gate(path if path.is_absolute() else PROJECT_ROOT / path, settings.reports_dir)
    for r in results:
        shown = "missing" if r.value is None else f"{r.value:.3f}"
        status = "PASS" if r.passed else "FAIL"
        typer.echo(f"{status}  {r.config:<12} {r.metric:<18} {shown} (min {r.threshold:.3f})")
    if not all(r.passed for r in results):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
