-- 002: Postgres full-text search next to the vectors, for hybrid retrieval.
-- A generated column keeps the tsvector in sync with heading/content automatically; the heading
-- gets weight 'A' so a match in a section title counts more than one in body text.
ALTER TABLE chunks
    ADD COLUMN tsv tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', heading), 'A') ||
        setweight(to_tsvector('english', content), 'B')
    ) STORED;

CREATE INDEX chunks_tsv_idx ON chunks USING gin (tsv);
