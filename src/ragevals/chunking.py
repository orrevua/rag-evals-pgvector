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


class MarkdownHeadingChunker:
    """Structure-aware chunking: one chunk per Markdown section, split further only if too long.

    * Sections follow the document's own headings, so a chunk is about *one* thing and its
      ``heading`` is accurate ("Query Parameters > Defaults").
    * Sections longer than ``max_chars`` are split on paragraph boundaries (never inside a
      code fence); each piece keeps the section's breadcrumb heading.
    * Sections shorter than ``min_chars`` (common in this corpus because the code samples are
      not included) are merged into the next section so we do not index near-empty chunks.
      The merged chunk keeps the heading of its longest part.
    """

    def __init__(self, max_chars: int = 1500, min_chars: int = 250) -> None:
        self.max_chars = max_chars
        self.min_chars = min_chars
        self.name = f"md{max_chars}"

    def _sections(self, doc: Document) -> list[tuple[str, str]]:
        """(breadcrumb, text) per heading-delimited section."""
        text = doc.text
        heads = _headings(text)
        sections: list[tuple[str, str]] = []
        trail: list[tuple[int, str]] = []  # (level, title) stack for breadcrumbs
        bounds = [h[0] for h in heads] + [len(text)]
        if heads and heads[0][0] > 0:
            sections.append((doc.title, text[: heads[0][0]]))
        for (start, level, title), end in zip(heads, bounds[1:], strict=True):
            while trail and trail[-1][0] >= level:
                trail.pop()
            trail.append((level, title))
            crumb = " > ".join(t for _, t in trail)
            sections.append((crumb, text[start:end]))
        return [(crumb, body.strip()) for crumb, body in sections if body.strip()]

    def _split_long(self, body: str) -> list[str]:
        if len(body) <= self.max_chars:
            return [body]
        paragraphs: list[str] = []
        current: list[str] = []
        in_fence = False
        for line in body.splitlines():
            if line.startswith("```"):
                in_fence = not in_fence
            if not line.strip() and not in_fence and current:
                paragraphs.append("\n".join(current))
                current = []
            elif line.strip() or in_fence:
                current.append(line)
        if current:
            paragraphs.append("\n".join(current))
        pieces: list[str] = []
        buf = ""
        for para in paragraphs:
            if buf and len(buf) + len(para) + 2 > self.max_chars:
                pieces.append(buf)
                buf = para
            else:
                buf = f"{buf}\n\n{para}" if buf else para
        if buf:
            pieces.append(buf)
        return pieces

    def chunk(self, doc: Document) -> list[Chunk]:
        merged: list[tuple[str, str]] = []
        pending: list[tuple[str, str]] = []
        for crumb, body in self._sections(doc):
            pending.append((crumb, body))
            if sum(len(b) for _, b in pending) >= self.min_chars:
                merged.append(self._merge(pending))
                pending = []
        if pending:
            if merged and sum(len(b) for _, b in pending) < self.min_chars:
                pending.insert(0, merged.pop())
            merged.append(self._merge(pending))

        chunks: list[Chunk] = []
        for crumb, body in merged:
            for piece in self._split_long(body):
                chunks.append(Chunk(f"{doc.source}#{len(chunks)}", doc.source, crumb, piece))
        return chunks

    @staticmethod
    def _merge(parts: list[tuple[str, str]]) -> tuple[str, str]:
        heading = max(parts, key=lambda p: len(p[1]))[0]
        return heading, "\n\n".join(body for _, body in parts)
