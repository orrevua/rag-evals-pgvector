-- 001: the vector store.
-- A "collection" is one (chunker, embedder) combination. Keeping them side by side in one table
-- lets every eval config query its own chunks without re-ingesting.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE collections (
    name        text PRIMARY KEY,           -- e.g. "fixed800__hash512"
    chunker     text NOT NULL,
    embedder    text NOT NULL,
    dim         integer NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
    id          bigserial PRIMARY KEY,
    collection  text NOT NULL REFERENCES collections(name) ON DELETE CASCADE,
    chunk_key   text NOT NULL,              -- "<source>#<n>", stable across re-ingests
    source      text NOT NULL,              -- file path relative to the corpus root
    heading     text NOT NULL,              -- section heading, used in citations
    content     text NOT NULL,
    -- No fixed dimension: different collections use different embedders (512, 384, 1536 dims).
    -- The trade-off is that an ANN index needs a fixed dimension; see LEARNING.md for the
    -- per-collection expression index you would add in production. With ~1k chunks an exact
    -- scan takes a few milliseconds, so we keep it simple.
    embedding   vector NOT NULL,
    UNIQUE (collection, chunk_key)
);

CREATE INDEX chunks_collection_idx ON chunks (collection);
