"""Document parsers: file -> plain text (markdown-ish, headings kept as `#` lines where possible).

`parse_file` dispatches on extension so adapters never need to know which parser applies.
"""
from __future__ import annotations

from pathlib import Path

from app.ingest.parsers import docx, md, pdf

_PARSERS = {".md": md.parse, ".markdown": md.parse, ".txt": md.parse, ".pdf": pdf.parse, ".docx": docx.parse}


def parse_file(path: Path) -> str:
    try:
        parser = _PARSERS[path.suffix.lower()]
    except KeyError:
        raise ValueError(f"no parser for {path.suffix!r} files ({path})") from None
    return parser(path)
