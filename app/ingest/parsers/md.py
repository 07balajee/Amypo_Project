"""Markdown / plain-text parser: the text is already in the form the chunker expects."""
from __future__ import annotations

from pathlib import Path


def parse(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")
