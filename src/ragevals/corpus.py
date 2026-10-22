"""Load the FastAPI tutorial Markdown and strip MkDocs-only noise.

The files under ``data/corpus/`` are kept exactly as upstream. Everything that only makes sense
to the MkDocs site generator is removed *here*, at load time, so the cleaning rules are code you
can test and change (and so re-syncing the corpus from upstream is a plain copy).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ragevals.text import TermStats

# --- cleaning rules -----------------------------------------------------------------------------

# <div class="termy"> ... </div> blocks are animated terminal sessions full of <font> tags.
_TERMY_RE = re.compile(r'<div class="termy">.*?</div>', re.DOTALL)
# {* ../../docs_src/first_steps/tutorial001_py310.py hl[3] *}: code includes resolved by MkDocs.
_INCLUDE_RE = re.compile(r"^\{\*.*?\*\}[ \t]*$", re.MULTILINE)
# "# First Steps { #first-steps }": explicit heading anchors.
_ANCHOR_RE = re.compile(r"[ \t]*\{[ \t]*#[^}\n]*\}[ \t]*$", re.MULTILINE)
# "/// tip", "/// note | Technical Details", "///", "//// tab | Python 3.10+", "////".
_ADMONITION_RE = re.compile(r"^/{3,4}.*$", re.MULTILINE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
# ```Python hl_lines="1 3" -> ```python
_FENCE_RE = re.compile(r"^```[ \t]*([A-Za-z]*)[^\n]*$", re.MULTILINE)
_BLANKS_RE = re.compile(r"\n{3,}")


def clean_markdown(raw: str) -> str:
    """Return readable Markdown: headings, prose, lists and code fences, without site markup."""
    text = _TERMY_RE.sub("", raw)
    text = _HTML_COMMENT_RE.sub("", text)
    text = _INCLUDE_RE.sub("", text)
    text = _ANCHOR_RE.sub("", text)
    text = _ADMONITION_RE.sub("", text)
    text = _IMAGE_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _HTML_TAG_RE.sub("", text)
    text = _FENCE_RE.sub(lambda m: "```" + m.group(1).lower(), text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = _BLANKS_RE.sub("\n\n", text)
    return text.strip() + "\n"


# --- documents ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Document:
    """One Markdown page. ``source`` is the path relative to the corpus root (cited in answers)."""

    source: str
    title: str
    text: str


def load_corpus(root: Path) -> list[Document]:
    """Load every ``*.md`` file under ``root`` (sorted, so ingestion is deterministic)."""
    documents: list[Document] = []
    for path in sorted(root.rglob("*.md")):
        if path.name.isupper() or path.name == "ATTRIBUTION.md":
            continue  # LICENSE / ATTRIBUTION notes are not tutorial content
        text = clean_markdown(path.read_text(encoding="utf-8"))
        title = next(
            (line[2:].strip() for line in text.splitlines() if line.startswith("# ")),
            path.stem,
        )
        documents.append(Document(source=path.relative_to(root).as_posix(), title=title, text=text))
    return documents


@lru_cache(maxsize=4)
def corpus_stats(root: Path) -> TermStats:
    """Document frequencies over the corpus pages (for IDF weighting). Cached per directory."""
    return TermStats.from_texts(d.text for d in load_corpus(root))
