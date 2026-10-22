"""Integration tests against a real Postgres + pgvector (skipped if DATABASE_URL is unreachable)."""

from ragevals.chunking import Chunk
from ragevals.embeddings import HashEmbedder
from ragevals.store import PgVectorStore

TEXTS = {
    "a.md": "Query parameters can have default values like skip and limit.",
    "b.md": "JWT tokens are signed with the HS256 algorithm.",
    "c.md": "CORS middleware configures allowed origins.",
}


def seed(pool, collection):
    store = PgVectorStore(pool)
    emb = HashEmbedder(dim=128)
    chunks = [Chunk(f"{s}#0", s, s.upper(), t) for s, t in TEXTS.items()]
    store.replace_collection(
        collection,
        chunker="test",
        embedder=emb.name,
        dim=emb.dim,
        chunks=chunks,
        embeddings=emb.embed_documents([c.content for c in chunks]),
    )
    return store, emb


def test_vector_search_ranks_relevant_chunk_first(pg_pool, collection_name):
    store, emb = seed(pg_pool, collection_name)
    try:
        assert store.count(collection_name) == 3
        hits = store.vector_search(collection_name, emb.embed_query("JWT signing algorithm"), k=2)
        assert hits[0].source == "b.md"
        assert hits[0].score > hits[1].score
    finally:
        store.drop_collection(collection_name)


def test_replace_collection_is_idempotent(pg_pool, collection_name):
    store, _ = seed(pg_pool, collection_name)
    try:
        seed(pg_pool, collection_name)
        assert store.count(collection_name) == 3
    finally:
        store.drop_collection(collection_name)
    assert store.count(collection_name) == 0


def test_keyword_search_uses_or_semantics_and_stemming(pg_pool, collection_name):
    store, _ = seed(pg_pool, collection_name)
    try:
        # "signing" stems to "sign" and matches "signed"; "unicorn" matches nothing but does not
        # turn the whole query into a miss, because the query is OR-ed.
        hits = store.keyword_search(collection_name, "signing unicorn tokens", k=3)
        assert [h.source for h in hits] == ["b.md"]
        assert store.keyword_search(collection_name, "the and of", k=3) == []
    finally:
        store.drop_collection(collection_name)


def test_hybrid_retriever_end_to_end(pg_pool, collection_name):
    from ragevals.retrieval import HybridRetriever, KeywordRetriever, VectorRetriever

    store, emb = seed(pg_pool, collection_name)
    try:
        retriever = HybridRetriever(
            VectorRetriever(store, emb, collection_name), KeywordRetriever(store, collection_name)
        )
        hits = retriever.retrieve("CORS allowed origins", k=2)
        assert hits[0].source == "c.md"
    finally:
        store.drop_collection(collection_name)
