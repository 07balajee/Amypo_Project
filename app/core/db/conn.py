"""SQLite connection helpers. Schemas applied idempotently on first connect."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from app.core.config import REPO_ROOT, get_settings

_SCHEMA_DIR = Path(__file__).resolve().parent
_lock = threading.Lock()
_initialized: set[str] = set()


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect(db_path: Path, schema_file: str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    key = str(db_path)
    with _lock:
        if key not in _initialized:
            schema_sql = (_SCHEMA_DIR / schema_file).read_text(encoding="utf-8")
            conn.executescript(schema_sql)
            conn.commit()
            _initialized.add(key)
    return conn


def get_ops_conn() -> sqlite3.Connection:
    settings = get_settings()
    return _connect(_resolve(settings.db.ops_db_path), "ops_schema.sql")


def get_amypo_conn() -> sqlite3.Connection:
    settings = get_settings()
    return _connect(_resolve(settings.db.amypo_db_path), "amypo_schema.sql")
