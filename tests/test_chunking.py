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


MD = Document(
    source="guide.md",
    title="Guide",
    text=(
        "# Guide\n\nIntro paragraph that is long enough to stand on its own as a chunk. " * 3
        + "\n\n## Install\n\nTiny.\n\n## Usage\n\n"
        + "Usage text explains how things work in detail. " * 10
        + "\n\n### Advanced\n\n"
        + ("A long paragraph about advanced usage. " * 20 + "\n\n") * 4
        + "```python\n# not a heading\nx = 1\n```\n"
    ),
)


def test_markdown_chunker_follows_headings_with_breadcrumbs():
    from ragevals.chunking import MarkdownHeadingChunker

    chunks = MarkdownHeadingChunker(max_chars=1000, min_chars=200).chunk(MD)
    headings = [c.heading for c in chunks]
    assert headings[0] == "Guide"
    # "Install" is tiny, so it is merged into the following "Usage" section.
    assert "Guide > Usage" in headings
    assert "Guide > Install" not in headings
    assert any(h == "Guide > Usage > Advanced" for h in headings)
    assert all(len(c.content) <= 1000 for c in chunks)
    assert "# not a heading" in chunks[-1].content  # code-fence lines are not headings
