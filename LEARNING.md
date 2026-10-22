# Learning guide

A study path through this repo, in the order the concepts build on each other, followed by
exercises to extend it. Each step names the file to read, what it teaches, and the official docs
worth opening next to it.

Before you start: `make setup && make ingest && make eval-all`, then keep
`reports/RESULTS.md` and `reports/baseline.md` open. Every concept below shows up as a number in
those files.

## Study path

### 1. The data: what are we even retrieving from?

- **`data/corpus/fastapi-tutorial/`** and **`src/ragevals/corpus.py`**
  Raw docs are messy. MkDocs include markers, admonitions and terminal-animation HTML would end
  up in your embeddings as noise. Cleaning happens in code (testable, repeatable), never by
  editing the source files. Try `uv run python -c "from ragevals.corpus import *; ..."` and
  compare a raw file with its cleaned text.
- Note what is *missing*: the tutorial's code samples live in `docs_src/` and are not part of
  this corpus. Some questions are hard for that reason alone.

### 2. Chunking: the unit of retrieval

- **`src/ragevals/chunking.py`**: `FixedSizeChunker` first (the naive baseline: windows with
  overlap that ignore structure), then `MarkdownHeadingChunker` (one chunk per section, with a
  breadcrumb heading, long sections split on paragraphs, tiny ones merged).
- Ask: what does a chunk's `heading` mean in each chunker? Why does citation quality depend on it?
- Compare `reports/baseline.md` with `reports/structured.md` on s13 and s25.

### 3. Embeddings: text to vectors

- **`src/ragevals/embeddings.py`**: one `Embedder` protocol, three implementations.
  `HashEmbedder` is the "hashing trick": deterministic, offline, but purely lexical.
  Understanding *why* it works at all (and where it cannot work, e.g. synonyms) is the point.
- Docs: [fastembed](https://qdrant.github.io/fastembed/),
  [BGE models](https://huggingface.co/BAAI/bge-small-en-v1.5),
  [OpenAI embeddings](https://platform.openai.com/docs/guides/embeddings).

### 4. Storage and search in Postgres

- **`src/ragevals/migrations/001_chunks.sql`**, **`002_fulltext.sql`** and
  **`src/ragevals/db.py`**: schema as numbered SQL files and a 30-line migration runner.
- **`src/ragevals/store.py`**: every SQL statement in one file. `vector_search` uses the `<=>`
  cosine-distance operator; `keyword_search` uses a generated, weighted `tsvector` column and an
  OR-rewritten `plainto_tsquery`.
- Docs: [pgvector README](https://github.com/pgvector/pgvector) (operators, HNSW/IVFFlat
  indexes), [PostgreSQL full-text search](https://www.postgresql.org/docs/16/textsearch.html),
  [generated columns](https://www.postgresql.org/docs/16/ddl-generated-columns.html),
  [psycopg 3](https://www.psycopg.org/psycopg3/docs/).

### 5. Retrieval strategies

- **`src/ragevals/retrieval.py`**: `VectorRetriever`, `KeywordRetriever`, `HybridRetriever` with
  `reciprocal_rank_fusion`, and `RerankingRetriever` (the two-stage pattern).
- **`src/ragevals/rerank.py`**: BM25 reranker (read the formula; it is 10 lines), cross-encoder
  via fastembed, listwise LLM reranker.
- Docs: [RRF paper (Cormack et al., 2009)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf),
  [BM25 (Robertson & Zaragoza)](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf),
  [sentence-transformers on cross-encoders](https://www.sbert.net/examples/cross_encoder/applications/README.html).

### 6. Generation and grounding

- **`src/ragevals/llm.py`**: the `Generator` protocol. `AnthropicGenerator` shows a grounded
  prompt (numbered passages, mandatory `[n]` citations, an exact refusal string).
  `ExtractiveGenerator` is the offline stand-in: IDF-weighted "is the answer in here?" check,
  then sentence extraction with citations.
- **`src/ragevals/pipeline.py`** and **`configs.py`**: how a named config becomes a concrete
  retriever + generator, and how `[n]` citations map back to file + heading.
- Docs: [Anthropic Messages API](https://docs.anthropic.com/en/api/messages),
  [streaming](https://docs.anthropic.com/en/docs/build-with-claude/streaming),
  [pricing](https://docs.anthropic.com/en/docs/about-claude/pricing).

### 7. Evaluation (the core of this project)

- **`evals/golden.jsonl`**: read ten items. Note `type`, `expected_sources`, `key_facts`,
  `should_refuse`. `tests/test_dataset.py` checks that every key fact really appears in its
  source page, which catches typos in a hand-written dataset.
- **`src/ragevals/evals/metrics.py`**: hit@k, recall@k, MRR, evidence@k, token F1, key-fact
  recall. Pure functions, unit tested in `tests/test_metrics.py`.
- **`src/ragevals/evals/judge.py`**: offline judge vs. LLM-as-judge with the fast model.
- **`src/ragevals/evals/runner.py`** and **`report.py`**: per-question rows, summaries by
  question type, Markdown reports, the `RESULTS.md` comparison.
- Docs: [Anthropic: define success criteria and build evals](https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests),
  [RAGAS metrics](https://docs.ragas.io/en/stable/concepts/metrics/) (for comparison with
  what is implemented here).

### 8. Production concerns

- **`src/ragevals/migrations/003_cache_and_request_log.sql`**, **`cache.py`**,
  **`observability.py`**: what goes into a cache key, why ingest clears the cache, JSON logs plus
  a queryable `request_log` table.
- **`src/ragevals/api.py`**: `POST /ask`, `POST /ask/stream` (SSE via `fastapi.sse`), the
  request-ID middleware, and why the streaming endpoint is an async wrapper around a sync
  generator (client disconnects).
- **`Dockerfile`**, **`docker-compose.yml`**, **`.github/workflows/ci.yml`**,
  **`src/ragevals/evals/gate.py`** + **`evals/gate.json`**: an eval as a CI quality gate.
- Docs: the FastAPI tutorial pages in this very corpus (`server-sent-events.md`,
  `middleware.md`, `dependencies/`), [Docker Compose](https://docs.docker.com/compose/),
  [GitHub Actions service containers](https://docs.github.com/en/actions/use-cases-and-examples/using-containerized-services/about-service-containers).

## Improve it yourself

Each exercise says how to know you are done: a test, or a number in a report.

1. **[easy] Hit@1 and hit@3.** Add them to `metrics.py`, the summary and `RESULTS.md`. Done when
   the table shows them; does any config now separate from the baseline on file-level hits?
2. **[easy] Cache TTL.** Add an `expires_at` column (new migration `004_...sql`) and ignore
   expired entries in `PgAnswerCache.get`. Done when a test with a 0-second TTL misses.
3. **[easy] Cost report.** Write `ragevals costs --since 7d` that queries `request_log` for
   requests, p50/p95 `total_ms`, tokens and cost per config. Pure SQL with `percentile_cont`.
4. **[medium] Paraphrased questions.** Add 15 golden items that ask the same things in user
   language ("my endpoint returns 422 for ?short=maybe, why?"). Re-run `eval-all` with `hash`
   and with `fastembed`. Done when you can say, with numbers, where dense embeddings start to win.
5. **[medium] Held-out split.** Split the golden set into `dev` and `test` (`split` field). Tune
   the fake generator's refusal threshold and the reranker's `k1`/`b` on `dev` only, then report
   `test`. How much did the committed numbers overstate refusal accuracy?
6. **[medium] ANN index.** The `embedding` column has no fixed dimension, so there is no index.
   Add a per-collection expression index, e.g.
   `CREATE INDEX ... USING hnsw ((embedding::vector(512)) vector_cosine_ops) WHERE collection = '...'`,
   rewrite `vector_search` to use the same expression, and confirm with `EXPLAIN ANALYZE`.
   Measure recall vs. exact search on the golden set.
7. **[medium] Tune RRF.** Make `rrf_k` and per-retriever weights configurable, add configs
   `hybrid-k10` / `hybrid-k100`, and compare MRR. Does the paper's 60 hold up here?
8. **[medium] Judge the judge.** With an API key, grade 20 answers yourself (0 / 0.5 / 1), then
   compare with `AnthropicJudge`. Report agreement (and Cohen's kappa). Change the prompt and
   measure again.
9. **[medium] Context compression.** Before generation, drop sentences from the top-k chunks
   that share no terms with the question. Measure input tokens (from `request_log`) and
   correctness. Fewer tokens, same answers?
10. **[hard] Multi-hop with query decomposition.** For questions the LLM marks as compound, split
    them into sub-questions, retrieve for each, and merge contexts. Track `multi_hop` recall@5
    and correctness in `RESULTS.md`.
11. **[hard] Real-model results.** Run `eval-all` with `EMBEDDER=fastembed` and the Anthropic
    generator + judge. Fill in the placeholders in `docs/writeup-draft.md`. Keep the offline
    results for CI and store real-model reports under `reports/real/`.
12. **[hard] Async end to end.** Switch the API to `psycopg_pool.AsyncConnectionPool` and
    `anthropic.AsyncAnthropic`, remove the threadpool bridge in `/ask/stream`, and load-test
    both versions (e.g. with `locust`) to see whether it matters at your concurrency.
