"""Heading-aware chunker. Chunk ids follow the `doc_id#c{n}` record_id format (CLAUDE.md §8).

1. Split the text into sections at markdown headings (`#`..`######`). Each section keeps its
   heading trail (e.g. "Unit 3: SQL") as a prefix so a chunk makes sense on its own.
2. A section that fits in `size_tokens` becomes one chunk. Larger sections are packed paragraph by
   paragraph, carrying the last `overlap_tokens` words into the next chunk; a single paragraph
   longer than the limit is cut into word windows.

"Tokens" are whitespace-separated words — a deliberately model-free approximation (MiniLM and
llama.cpp tokenizers both yield somewhat more tokens than words, so 350 words stays well inside the
retrieval context budget).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    ordinal: int
    text: str
    token_count: int


def count_tokens(text: str) -> int:
    return len(text.split())


def _sections(text: str) -> list[tuple[str, list[str]]]:
    """-> [(heading_trail, paragraphs)], in document order."""
    trail: list[tuple[int, str]] = []
    sections: list[tuple[str, list[str]]] = []
    paragraphs: list[str] = []
    buf: list[str] = []

    def flush_para() -> None:
        if buf:
            para = " ".join(line.strip() for line in buf).strip()
            if para:
                paragraphs.append(para)
            buf.clear()

    def flush_section() -> None:
        flush_para()
        if paragraphs:
            sections.append((" > ".join(h for _, h in trail), paragraphs.copy()))
            paragraphs.clear()

    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            flush_section()
            level = len(m.group(1))
            trail[:] = [(lvl, h) for lvl, h in trail if lvl < level]
            trail.append((level, m.group(2)))
        elif not line.strip():
            flush_para()
        elif line.lstrip().startswith(("- ", "* ", "| ")) or re.match(r"^\s*\d+\.\s", line):
            flush_para()  # list items / table rows stay on their own line
            buf.append(line)
            flush_para()
        else:
            buf.append(line)
    flush_section()
    return sections


def _windows(words: list[str], size: int, overlap: int) -> list[list[str]]:
    step = max(1, size - overlap)
    out = []
    for start in range(0, len(words), step):
        out.append(words[start : start + size])
        if start + size >= len(words):
            break
    return out


def chunk_text(doc_id: str, text: str, size_tokens: int = 350, overlap_tokens: int = 60) -> list[Chunk]:
    bodies: list[str] = []
    for trail, paragraphs in _sections(text):
        prefix = f"{trail}\n" if trail else ""
        budget = max(1, size_tokens - count_tokens(trail))
        current: list[str] = []
        current_len = 0
        for para in paragraphs:
            n = count_tokens(para)
            if n > budget:  # oversize paragraph: flush, then window it
                if current:
                    bodies.append(prefix + "\n".join(current))
                for win in _windows(para.split(), budget, overlap_tokens):
                    bodies.append(prefix + " ".join(win))
                current, current_len = [], 0
                continue
            if current and current_len + n > budget:
                bodies.append(prefix + "\n".join(current))
                tail = " ".join(" ".join(current).split()[-overlap_tokens:]) if overlap_tokens else ""
                current = [tail] if tail else []
                current_len = count_tokens(tail)
            current.append(para)
            current_len += n
        if current:
            bodies.append(prefix + "\n".join(current))
    return [
        Chunk(chunk_id=f"{doc_id}#c{i}", doc_id=doc_id, ordinal=i, text=body, token_count=count_tokens(body))
        for i, body in enumerate(bodies)
    ]
