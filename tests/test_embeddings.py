import numpy as np
import pytest

from ragevals.embeddings import HashEmbedder, get_embedder


def test_hash_embedder_is_deterministic_and_normalised():
    emb = HashEmbedder(dim=256)
    a = emb.embed_query("How do I declare query parameters?")
    assert a == emb.embed_query("How do I declare query parameters?")
    assert len(a) == 256
    assert np.isclose(np.linalg.norm(a), 1.0)


def test_hash_embedder_similarity_is_lexical():
    emb = HashEmbedder()
    q = np.array(emb.embed_query("query parameter default values"))
    near = np.array(emb.embed_documents(["Query parameters can have default values."])[0])
    far = np.array(emb.embed_documents(["JWT tokens are signed with HS256."])[0])
    assert q @ near > q @ far


def test_get_embedder_rejects_unknown():
    with pytest.raises(ValueError):
        get_embedder("word2vec")
