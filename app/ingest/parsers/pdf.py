"""PDF parser (pdfplumber). Page text is joined with blank lines so paragraphs stay separable."""
from __future__ import annotations

from pathlib import Path


def parse(path: Path) -> str:
    import pdfplumber  # heavy import, only needed when a PDF is actually ingested

    with pdfplumber.open(path) as pdf:
        pages = [(page.extract_text() or "").strip() for page in pdf.pages]
    return "\n\n".join(p for p in pages if p)
