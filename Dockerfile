# Image for the API and the one-shot ingest/eval job. Offline by default (hash embedder + fake LLM).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first, in their own layer: code changes do not reinstall them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY data ./data
COPY evals ./evals
RUN uv sync --frozen --no-dev

# Run as an unprivileged user. If you bind-mount ./reports, it must be writable by uid 1000.
RUN useradd --uid 1000 --create-home app && mkdir -p /app/reports && chown -R app /app/reports
USER app

EXPOSE 8000
CMD ["uvicorn", "ragevals.api:app", "--host", "0.0.0.0", "--port", "8000"]
