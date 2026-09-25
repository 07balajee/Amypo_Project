"""DOCX parser (python-docx). Heading styles become markdown `#` lines so the chunker can
split on them the same way it does for markdown sources."""
from __future__ import annotations

from pathlib import Path


def parse(path: Path) -> str:
    import docx  # python-docx

    lines: list[str] = []
    for para in docx.Document(str(path)).paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = para.style.name if para.style is not None else ""
        if style == "Title":
            lines.append(f"# {text}")
        elif style.startswith("Heading "):
            level = style.removeprefix("Heading ").strip()
            depth = int(level) + 1 if level.isdigit() else 2
            lines.append(f"{'#' * min(depth, 6)} {text}")
        else:
            lines.append(text)
    return "\n\n".join(lines)
