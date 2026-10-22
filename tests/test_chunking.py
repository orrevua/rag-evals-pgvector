from ragevals.chunking import FixedSizeChunker
from ragevals.corpus import Document

DOC = Document(
    source="demo.md",
    title="Demo",
    text="# Demo\n\nIntro text.\n\n## First\n\n"
    + ("alpha " * 120)
    + "\n\n## Second\n\n"
    + ("beta " * 120),
)


def test_fixed_chunker_sizes_overlap_and_keys():
    chunks = FixedSizeChunker(size=300, overlap=50).chunk(DOC)
    assert len(chunks) > 3
    assert all(len(c.content) <= 300 for c in chunks)
    assert [c.chunk_key for c in chunks] == [f"demo.md#{i}" for i in range(len(chunks))]
    assert chunks[0].heading == "Demo"
    assert chunks[-1].heading == "Second"


def test_fixed_chunker_is_deterministic():
    chunker = FixedSizeChunker(size=300, overlap=50)
    assert chunker.chunk(DOC) == chunker.chunk(DOC)


def test_fixed_chunker_covers_all_text():
    chunks = FixedSizeChunker(size=300, overlap=50).chunk(DOC)
    joined = " ".join(c.content for c in chunks)
    assert joined.count("beta") >= 120
