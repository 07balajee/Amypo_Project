"""Writes adapter output into the amypo database (MySQL in the services, SQLite in tests).

Each part is a full refresh inside one transaction: delete the part's tables (children first),
then insert (parents first). Re-running is safe and leaves exactly the adapter's current data.

Parts:
  tables    structured records (students, grades, attendance, placement, ...)
  docs      documents + chunks (chunked here with qa.chunking settings)
  training  past_queries + router_prompts + router_scenarios + qa_benchmark
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.db.conn import DBConn
from app.ingest.adapters.base import (
    BENCHMARK_COLUMNS,
    PAST_QUERY_COLUMNS,
    TABLE_COLUMNS,
    DataAdapter,
    Row,
)
from app.ingest.chunker import chunk_text

PARTS = ("tables", "docs", "training")

# How a structured record_id `table:v1:v2...` maps to columns (CLAUDE.md §8 record_id format).
RECORD_ID_KEYS: dict[str, tuple[str, ...]] = {
    "students": ("id",),
    "users": ("user_id",),
    "courses": ("code",),
    "enrollments": ("student_id", "course_code", "semester"),
    "grades": ("student_id", "course_code"),
    "attendance": ("student_id", "course_code"),
    "schedules": ("course_code", "session_type", "day_or_date"),
    "skills": ("id",),
    "student_skills": ("student_id", "skill_id"),
    "companies": ("id",),
    "company_criteria": ("company_id",),
    "module_skill_map": ("skill_id", "module"),
}


@dataclass
class LoadReport:
    counts: dict[str, int] = field(default_factory=dict)
    index_version: str | None = None
    dangling_record_ids: list[str] = field(default_factory=list)


def _insert(conn: DBConn, table: str, cols: tuple[str, ...], rows: list[Row]) -> int:
    for i, row in enumerate(rows):
        if set(row) != set(cols):
            raise ValueError(
                f"{table} row {i}: columns {sorted(row)} != expected {sorted(cols)}"
            )
    if rows:
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        conn.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
    return len(rows)


def _delete(conn: DBConn, tables: list[str]) -> None:
    for table in tables:
        conn.execute(f"DELETE FROM {table}")


def load_tables(adapter: DataAdapter, conn: DBConn, report: LoadReport) -> None:
    tables = adapter.load_tables()
    missing = set(TABLE_COLUMNS) - set(tables)
    if missing:
        raise ValueError(f"adapter {adapter.name!r} returned no rows for tables: {sorted(missing)}")
    _delete(conn, list(reversed(TABLE_COLUMNS)))
    for table, cols in TABLE_COLUMNS.items():
        report.counts[table] = _insert(conn, table, cols, tables[table])


def load_docs(adapter: DataAdapter, conn: DBConn, report: LoadReport) -> None:
    cfg = get_settings().qa.chunking
    docs = adapter.load_documents()
    chunks = [
        c
        for d in docs
        for c in chunk_text(d.doc_id, d.text, cfg.size_tokens, cfg.overlap_tokens)
    ]
    digest = hashlib.sha256()
    for c in chunks:
        digest.update(c.chunk_id.encode())
        digest.update(c.text.encode())
    version = f"v-{digest.hexdigest()[:12]}"  # changes whenever content or chunking changes
    _delete(conn, ["chunks", "documents"])
    report.counts["documents"] = _insert(
        conn,
        "documents",
        ("doc_id", "title", "doc_type", "source_path", "index_version"),
        [
            {"doc_id": d.doc_id, "title": d.title, "doc_type": d.doc_type,
             "source_path": d.source_path, "index_version": version}
            for d in docs
        ],
    )
    report.counts["chunks"] = _insert(
        conn,
        "chunks",
        ("chunk_id", "doc_id", "ordinal", "text", "token_count", "index_version"),
        [
            {"chunk_id": c.chunk_id, "doc_id": c.doc_id, "ordinal": c.ordinal, "text": c.text,
             "token_count": c.token_count, "index_version": version}
            for c in chunks
        ],
    )
    report.index_version = version


def load_training(adapter: DataAdapter, conn: DBConn, report: LoadReport) -> None:
    past = adapter.load_past_queries()
    benchmarks = adapter.load_benchmarks()
    _delete(conn, ["past_queries", *BENCHMARK_COLUMNS])
    report.counts["past_queries"] = _insert(conn, "past_queries", PAST_QUERY_COLUMNS, past)
    for name, cols in BENCHMARK_COLUMNS.items():
        report.counts[name] = _insert(conn, name, cols, benchmarks.get(name, []))


def record_exists(conn: DBConn, record_id: str) -> bool:
    """True if `record_id` (chunk `doc#cN` or structured `table:pk...`) names a real row."""
    if "#c" in record_id:
        sql, params = "SELECT 1 FROM chunks WHERE chunk_id = ?", (record_id,)
    else:
        table, _, rest = record_id.partition(":")
        keys = RECORD_ID_KEYS.get(table)
        # The last key takes the remainder, so values may contain ':' (e.g. module names).
        values = rest.split(":", len(keys) - 1) if rest and keys else []
        if keys is None or len(values) != len(keys):
            return False
        where = " AND ".join(f"{k} = ?" for k in keys)
        sql, params = f"SELECT 1 FROM {table} WHERE {where}", tuple(values)
    return conn.execute(sql, params).fetchone() is not None


def find_dangling_record_ids(conn: DBConn) -> list[str]:
    """Record ids cited by past_queries / qa_benchmark that don't resolve to a row."""
    cited: set[str] = set()
    for r in conn.execute("SELECT record_id FROM past_queries").fetchall():
        cited.add(r["record_id"])
    for r in conn.execute("SELECT gold_record_ids_json FROM qa_benchmark").fetchall():
        cited.update(json.loads(r["gold_record_ids_json"]))
    return sorted(rid for rid in cited if not record_exists(conn, rid))


def load_all(adapter: DataAdapter, conn: DBConn, parts: tuple[str, ...] = PARTS) -> LoadReport:
    unknown = set(parts) - set(PARTS)
    if unknown:
        raise ValueError(f"unknown parts {sorted(unknown)}; choose from {PARTS}")
    report = LoadReport()
    if "tables" in parts:
        load_tables(adapter, conn, report)
    if "docs" in parts:
        load_docs(adapter, conn, report)
    if "training" in parts:
        load_training(adapter, conn, report)
    report.dangling_record_ids = find_dangling_record_ids(conn)
    return report
