"""CSV parser for tabular sources: returns rows as dicts of strings (types are the adapter's job)."""
from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
