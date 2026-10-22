-- 003: production polish. An answer cache and a per-request log for tokens, cost and latency.

-- Keyed by a hash of (normalised question, config, generator, embedder): change any of those and
-- you get a different key, so a model or retrieval change never serves stale answers.
CREATE TABLE answer_cache (
    cache_key    text PRIMARY KEY,
    question     text NOT NULL,
    config       text NOT NULL,
    response     jsonb NOT NULL,
    hits         integer NOT NULL DEFAULT 0,
    created_at   timestamptz NOT NULL DEFAULT now(),
    last_hit_at  timestamptz
);

-- One row per API request. Query it with plain SQL, e.g. p95 latency per config:
--   SELECT config, percentile_cont(0.95) WITHIN GROUP (ORDER BY total_ms) FROM request_log
--   GROUP BY config;
CREATE TABLE request_log (
    id             bigserial PRIMARY KEY,
    created_at     timestamptz NOT NULL DEFAULT now(),
    request_id     text NOT NULL,
    endpoint       text NOT NULL,
    config         text NOT NULL,
    question       text NOT NULL,
    cached         boolean NOT NULL,
    refused        boolean,
    model          text,
    input_tokens   integer NOT NULL DEFAULT 0,
    output_tokens  integer NOT NULL DEFAULT 0,
    cost_usd       numeric(12, 6) NOT NULL DEFAULT 0,
    retrieval_ms   real,
    generation_ms  real,
    total_ms       real NOT NULL,
    n_sources      integer,
    error          text
);

CREATE INDEX request_log_created_at_idx ON request_log (created_at);
