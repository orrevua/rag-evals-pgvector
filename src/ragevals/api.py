"""HTTP API.

* ``POST /ask``         answer + cited sources (file + heading), served from cache when possible
* ``POST /ask/stream``  the same answer as Server-Sent Events: ``token`` events, then ``done``
* ``GET  /configs``     available pipeline configs
* ``GET  /health``

Every request is logged as one JSON line and one ``request_log`` row (tokens, cost, latency).
Run it with ``make serve`` (``uvicorn ragevals.api:app``); interactive docs at ``/docs``.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import iterate_in_threadpool

from ragevals.cache import AnswerCache, PgAnswerCache, cache_key
from ragevals.configs import CONFIGS, get_config
from ragevals.corpus import corpus_stats
from ragevals.db import make_pool
from ragevals.embeddings import get_embedder
from ragevals.llm import get_generator
from ragevals.observability import PgRequestLog, RequestLog, RequestRecord, configure_logging
from ragevals.pipeline import Answer, RagPipeline, build_pipeline
from ragevals.settings import get_settings
from ragevals.store import PgVectorStore

DEFAULT_CONFIG = "baseline"


# --- request / response models ------------------------------------------------------------------


class AskRequest(BaseModel):
    question: str = Field(
        min_length=3, max_length=1000, examples=["How do I declare a query parameter?"]
    )
    config: str = Field(default=DEFAULT_CONFIG, description="Config name, see GET /configs")
    use_cache: bool = Field(default=True, description="Set false to force a fresh answer")

    @field_validator("config")
    @classmethod
    def known_config(cls, value: str) -> str:
        # Validated here (a 422) rather than in the endpoint, because the streaming endpoint is a
        # generator: by the time its body runs, the 200 response headers are already sent.
        if value not in CONFIGS:
            raise ValueError(f"unknown config {value!r}; available: {', '.join(CONFIGS)}")
        return value


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
    cached: bool = False


# --- wiring -------------------------------------------------------------------------------------


@dataclass
class Services:
    """Everything the endpoints need. Tests build one by hand with in-memory fakes."""

    pipeline_for: Callable[[str], RagPipeline]
    cache: AnswerCache | None = None
    request_log: RequestLog | None = None
    embedder_name: str = "unknown"
    _closers: list[Callable[[], None]] = field(default_factory=list)

    def close(self) -> None:
        for closer in self._closers:
            closer()


def build_services() -> Services:
    settings = get_settings()
    pool = make_pool(settings.database_url, max_size=10)
    store = PgVectorStore(pool)
    embedder = get_embedder()
    generator = get_generator()
    stats = corpus_stats(settings.corpus_dir)
    pipelines: dict[str, RagPipeline] = {}

    def pipeline_for(name: str) -> RagPipeline:
        if name not in pipelines:
            pipelines[name] = build_pipeline(get_config(name), store, embedder, generator, stats)
        return pipelines[name]

    return Services(
        pipeline_for=pipeline_for,
        cache=PgAnswerCache(pool),
        request_log=PgRequestLog(pool),
        embedder_name=embedder.name,
        _closers=[pool.close],
    )


def get_services(request: Request) -> Services:
    return request.app.state.services


# The "Annotated dependency" pattern from the FastAPI tutorial (dependencies/index.md).
ServicesDep = Annotated[Services, Depends(get_services)]


def _key(services: Services, pipeline: RagPipeline, question: str) -> str:
    return cache_key(
        question, pipeline.config.name, pipeline.generator.name, services.embedder_name
    )


def _log(
    services: Services,
    request: Request,
    endpoint: str,
    body: AskRequest,
    started: float,
    response: dict | None,
    cached: bool,
    error: str | None = None,
) -> None:
    if services.request_log is None:
        return
    rec = RequestRecord(
        request_id=request.state.request_id,
        endpoint=endpoint,
        config=body.config,
        question=body.question,
        cached=cached,
        total_ms=round((time.perf_counter() - started) * 1000, 2),
        error=error,
    )
    if response is not None:
        usage = response["usage"]
        timings = response.get("timings_ms", {})
        rec.refused = response["refused"]
        rec.model = usage["model"]
        rec.n_sources = len(response["sources"])
        if not cached:  # a cache hit costs nothing and took no retrieval/generation time
            rec.input_tokens = usage["input_tokens"]
            rec.output_tokens = usage["output_tokens"]
            rec.cost_usd = usage["cost_usd"]
            rec.retrieval_ms = timings.get("retrieval")
            rec.generation_ms = timings.get("generation")
    services.request_log.record(rec)


def create_app(services: Services | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
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

    @app.middleware("http")
    async def request_id_and_timing(request: Request, call_next):
        # The middleware pattern from the tutorial (middleware.md): code before and after
        # the response. Clients can pass their own X-Request-ID to correlate logs.
        request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Process-Time"] = f"{time.perf_counter() - started:.4f}"
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/configs")
    def configs() -> dict[str, str]:
        return {name: c.description for name, c in CONFIGS.items()}

    @app.post("/ask", response_model=AskResponse)
    def ask(body: AskRequest, request: Request, services: ServicesDep) -> dict:
        # A plain ``def`` endpoint: FastAPI runs it in a threadpool, so the blocking DB and LLM
        # calls inside do not block the event loop.
        started = time.perf_counter()
        pipeline = services.pipeline_for(body.config)
        key = _key(services, pipeline, body.question)
        if body.use_cache and services.cache and (hit := services.cache.get(key)):
            response = {**hit, "cached": True}
            _log(services, request, "/ask", body, started, response, cached=True)
            return response
        try:
            response = pipeline.answer(body.question).to_dict()
        except Exception as exc:
            _log(services, request, "/ask", body, started, None, False, error=repr(exc))
            raise
        if services.cache and not response["refused"]:
            services.cache.put(key, body.question, body.config, response)
        _log(services, request, "/ask", body, started, response, cached=False)
        return {**response, "cached": False}

    @app.post("/ask/stream", response_class=EventSourceResponse)
    async def ask_stream(
        body: AskRequest, request: Request, services: ServicesDep
    ) -> AsyncIterator[ServerSentEvent]:
        """Server-Sent Events: ``token`` events with text deltas, then one ``done`` event whose
        data is the same JSON object ``POST /ask`` returns. Uses ``fastapi.sse`` (FastAPI 0.135+).
        """
        # The blocking work (DB, LLM) lives in a *sync* generator that we drive from a
        # threadpool. This async wrapper exists for one reason: when the client hangs up,
        # Starlette cancels *this* generator, and its ``finally`` lets us close the sync one so
        # that its own ``finally`` (which logs the request) runs.
        events = _stream_events(body, request, services)
        try:
            async for event in iterate_in_threadpool(events):
                yield event
        finally:
            with contextlib.suppress(ValueError):  # still running in its thread: let it finish
                events.close()

    return app


def _stream_events(
    body: AskRequest, request: Request, services: Services
) -> Iterator[ServerSentEvent]:
    """The events for ``POST /ask/stream``; runs in a worker thread (see ``ask_stream``)."""
    started = time.perf_counter()
    pipeline = services.pipeline_for(body.config)
    key = _key(services, pipeline, body.question)
    if body.use_cache and services.cache and (hit := services.cache.get(key)):
        response = {**hit, "cached": True}
        _log(services, request, "/ask/stream", body, started, response, cached=True)
        yield ServerSentEvent(event="token", data={"text": response["answer"]})
        yield ServerSentEvent(event="done", data=response)
        return
    logged = False
    try:
        for item in pipeline.stream(body.question):
            if isinstance(item, Answer):
                response = {**item.to_dict(), "cached": False}
                if services.cache and not item.refused:
                    services.cache.put(key, body.question, body.config, item.to_dict())
                _log(services, request, "/ask/stream", body, started, response, False)
                logged = True
                yield ServerSentEvent(event="done", data=response)
            else:
                yield ServerSentEvent(event="token", data={"text": item})
    except Exception as exc:
        _log(services, request, "/ask/stream", body, started, None, False, repr(exc))
        logged = True
        yield ServerSentEvent(event="error", data={"detail": "generation failed"})
    finally:
        # The client can hang up mid-stream (the generator is then closed); still log it.
        if not logged:
            _log(services, request, "/ask/stream", body, started, None, False, "disconnected")


app = create_app()
