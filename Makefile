# Common tasks. Everything runs offline by default (hash embedder + fake extractive LLM).
SHELL := /bin/bash
export DATABASE_URL ?= postgresql://postgres:postgres@localhost:5432/p1_rag
CONFIG ?= baseline

.PHONY: setup db ingest serve test lint format demo eval eval-all

setup:  ## install deps and prepare the database (create + migrate)
	uv sync
	uv run ragevals init-db

db:  ## apply pending SQL migrations
	uv run ragevals init-db

ingest:  ## chunk + embed the corpus for every config
	uv run ragevals ingest --config all

serve:  ## run the API on :8000
	uv run uvicorn ragevals.api:app --reload --port 8000

eval:  ## evaluate one config (CONFIG=baseline) -> reports/$(CONFIG).json + .md
	uv run ragevals eval --config $(CONFIG)

eval-all:  ## evaluate every config and regenerate reports/RESULTS.md
	uv run ragevals eval-all

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

demo: setup ingest  ## end-to-end: ingest, then answer two questions (one unanswerable)
	uv run ragevals ask "What are the default values of skip and limit in the query parameters example?"
	uv run ragevals ask "How do I deploy FastAPI to AWS Lambda with Mangum?"
