"""Adapter for the generated data in `data.synthetic_dir` (scripts/gen_synthetic.py writes it).

This is the only module that knows the synthetic file layout:
  docs/manifest.yaml + docs/*          documents (md/pdf/docx)
  tables/<table>.csv                   one CSV per TABLE_COLUMNS entry
  past_queries.csv
  router_prompts.jsonl, router_scenarios.jsonl, qa_benchmark.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from app.core.config import REPO_ROOT, get_settings
from app.ingest.adapters.base import (
    BENCHMARK_COLUMNS,
    DOC_TYPES,
    PAST_QUERY_COLUMNS,
    TABLE_COLUMNS,
    DataAdapter,
    Row,
    SourceDocument,
)
from app.ingest.parsers import parse_file
from app.ingest.parsers.csv import read_rows

# Column -> type for CSV values (CSV gives strings). Unlisted columns stay str; "" -> None.
_INT = {"year", "backlogs", "projects_count", "credits", "proficiency", "max_backlogs", "t_sec"}
_FLOAT = {
    "cgpa", "coding_score", "internal", "external", "total", "attendance_pct",
    "min_cgpa", "min_attendance", "weight", "ctc_lpa",
}


def _typed(col: str, value: str) -> Any:
    if value == "":
        return None
    if col in _INT:
        return int(value)
    if col in _FLOAT:
        return float(value)
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _display_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else path.as_posix()


class SyntheticAdapter(DataAdapter):
    name = "synthetic"

    def __init__(self, root: Path | None = None) -> None:
        if root is None:
            root = Path(get_settings().data.synthetic_dir)
            if not root.is_absolute():
                root = REPO_ROOT / root
        self.root = root
        if not (self.root / "docs" / "manifest.yaml").exists():
            raise FileNotFoundError(
                f"no synthetic data in {self.root}; run `python scripts/gen_synthetic.py` first"
            )

    def load_documents(self) -> list[SourceDocument]:
        manifest = yaml.safe_load((self.root / "docs" / "manifest.yaml").read_text(encoding="utf-8"))
        docs = []
        for entry in manifest["documents"]:
            if entry["doc_type"] not in DOC_TYPES:
                raise ValueError(f"{entry['doc_id']}: unknown doc_type {entry['doc_type']!r}")
            path = self.root / "docs" / entry["file"]
            docs.append(
                SourceDocument(
                    doc_id=entry["doc_id"],
                    title=entry["title"],
                    doc_type=entry["doc_type"],
                    source_path=_display_path(path),
                    text=parse_file(path),
                )
            )
        return docs

    def load_tables(self) -> dict[str, list[Row]]:
        tables: dict[str, list[Row]] = {}
        for table, cols in TABLE_COLUMNS.items():
            rows = read_rows(self.root / "tables" / f"{table}.csv")
            tables[table] = [{c: _typed(c, r[c]) for c in cols} for r in rows]
        return tables

    def load_past_queries(self) -> list[Row]:
        rows = read_rows(self.root / "past_queries.csv")
        return [{c: r[c] for c in PAST_QUERY_COLUMNS} for r in rows]

    def load_benchmarks(self) -> dict[str, list[Row]]:
        out: dict[str, list[Row]] = {}
        for name, cols in BENCHMARK_COLUMNS.items():
            items = _read_jsonl(self.root / f"{name}.jsonl")
            if name == "qa_benchmark":
                for it in items:
                    it["gold_record_ids_json"] = json.dumps(it.pop("gold_record_ids"))
            out[name] = [{c: it.get(c) for c in cols} for it in items]
        return out
