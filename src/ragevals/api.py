"""HTTP API. ``POST /ask`` returns an answer with cited sources (file + heading).

Run it with ``make serve`` (``uvicorn ragevals.api:app``). Interactive docs at ``/docs``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from ragevals.configs import CONFIGS, get_config
from ragevals.db import make_pool
from ragevals.embeddings import get_embedder
from ragevals.llm import get_generator
from ragevals.pipeline import RagPipeline, build_pipeline
from ragevals.settings import get_settings
from ragevals.store import PgVectorStore

DEFAULT_CONFIG = "baseline"


# --- request / response models ------------------------------------------------------------------


class AskRequest(BaseModel):
    question: str = Field(
        min_length=3, max_length=1000, examples=["How do I declare a query parameter?"]
    )
    config: str = Field(default=DEFAULT_CONFIG, description="Config name, see GET /configs")


class SourceOut(BaseModel):
    source: str = Field(description="File path relative to the corpus root")
    heading: str
    chunk_key: str
    score: float


class UsageOut(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class AskResponse(BaseModel):
    answer: str
    refused: bool
    sources: list[SourceOut]
    config: str
    generator: str
    usage: UsageOut
    timings_ms: dict[str, float]


# --- wiring -------------------------------------------------------------------------------------


@dataclass
class Services:
    """Everything the endpoints need. Tests build one by hand with fakes."""

    pipeline_for: Callable[[str], RagPipeline]
    _closers: list[Callable[[], None]] = field(default_factory=list)

    def close(self) -> None:
        for closer in self._closers:
            closer()


def build_services() -> Services:
    settings = get_settings()
    pool = make_pool(settings.database_url)
    store = PgVectorStore(pool)
    embedder = get_embedder()
    generator = get_generator()
    pipelines: dict[str, RagPipeline] = {}

    def pipeline_for(name: str) -> RagPipeline:
        if name not in pipelines:
            pipelines[name] = build_pipeline(get_config(name), store, embedder, generator)
        return pipelines[name]

    return Services(pipeline_for=pipeline_for, _closers=[pool.close])


def get_services(request: Request) -> Services:
    return request.app.state.services


# The "Annotated dependency" pattern from the FastAPI tutorial (dependencies/index.md).
ServicesDep = Annotated[Services, Depends(get_services)]


def create_app(services: Services | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.services = services or build_services()
        try:
            yield
        finally:
            if services is None:
                app.state.services.close()

    app = FastAPI(
        title="ragevals",
        summary="RAG question answering over the FastAPI tutorial, with an evaluation suite.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/configs")
    def configs() -> dict[str, str]:
        return {name: c.description for name, c in CONFIGS.items()}

    @app.post("/ask", response_model=AskResponse)
    def ask(body: AskRequest, services: ServicesDep) -> dict:
        # A plain ``def`` endpoint: FastAPI runs it in a threadpool, so the blocking DB and LLM
        # calls inside do not block the event loop.
        if body.config not in CONFIGS:
            raise HTTPException(status_code=404, detail=f"Unknown config {body.config!r}")
        answer = services.pipeline_for(body.config).answer(body.question)
        return answer.to_dict()

    return app


app = create_app()
