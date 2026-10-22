"""Chunkers turn a Document into retrievable pieces.

Every chunk keeps ``source`` (the file) and ``heading`` (the section it came from) so answers
can cite "file + heading". Chunkers must be deterministic: the same corpus gives the same
``chunk_key`` values, which is what makes re-ingestion an idempotent upsert.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from ragevals.corpus import Document

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    chunk_key: str  # stable id: "<source>#<index>"
    source: str
    heading: str
    content: str


class Chunker(Protocol):
    name: str

    def chunk(self, doc: Document) -> list[Chunk]: ...


def _headings(text: str) -> list[tuple[int, int, str]]:
    """(offset, level, title) for each Markdown heading, ignoring lines inside code fences."""
    out: list[tuple[int, int, str]] = []
    in_fence = False
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and (m := _HEADING_RE.match(line)):
            out.append((offset, len(m.group(1)), m.group(2).strip()))
        offset += len(line)
    return out


def heading_at(headings: list[tuple[int, int, str]], offset: int, default: str) -> str:
    """The most recent heading at or before ``offset``."""
    current = default
    for start, _level, title in headings:
        if start > offset:
            break
        current = title
    return current


class FixedSizeChunker:
    """The naive baseline: fixed-size character windows with overlap.

    It ignores document structure entirely, so a window can start in the middle of one section
    and end in the middle of the next. That is exactly the weakness the structure-aware chunker
    fixes later, and why the baseline exists: you need something to measure upgrades against.
    """

    def __init__(self, size: int = 800, overlap: int = 100) -> None:
        if overlap >= size:
            raise ValueError("overlap must be smaller than size")
        self.size = size
        self.overlap = overlap
        self.name = f"fixed{size}"

    def chunk(self, doc: Document) -> list[Chunk]:
        text = doc.text
        headings = _headings(text)
        chunks: list[Chunk] = []
        start = 0
        while start < len(text):
            end = min(start + self.size, len(text))
            if end < len(text):
                # Snap to whitespace so we do not cut words in half.
                lo = start + int(self.size * 0.8)
                cut = max(text.rfind(" ", lo, end), text.rfind("\n", lo, end))
                if cut != -1:
                    end = cut
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    Chunk(
                        chunk_key=f"{doc.source}#{len(chunks)}",
                        source=doc.source,
                        heading=heading_at(headings, start, doc.title),
                        content=piece,
                    )
                )
            if end >= len(text):
                break
            start = max(end - self.overlap, start + 1)
        return chunks
