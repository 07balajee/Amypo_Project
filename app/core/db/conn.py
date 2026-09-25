"""Database connection helpers. Schemas applied idempotently on first connect.

Backend is chosen by `db.backend`: `mysql` for the running services, `sqlite` for the test suite
(no server needed). Callers use one API for both:

    with get_ops_conn() as conn:
        rows = conn.execute("SELECT * FROM route_log WHERE ts >= ?", (since,)).fetchall()

- Write placeholders as `?`; they are translated to `%s` for MySQL.
- Rows support `row["column"]` on both backends.
- Leaving the `with` block commits on success, rolls back on error, and closes the connection.
- Stick to SQL both dialects accept (e.g. `REPLACE INTO`, not `INSERT OR REPLACE`).
"""
from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Self

from app.core.config import get_settings

_SCHEMA_DIR = Path(__file__).resolve().parent

# schema file -> {version: [statements]}. Upgrades databases created by an older schema file
# (CREATE TABLE IF NOT EXISTS never adds columns). Fresh databases are inserted at the latest
# version by the schema file itself, so these only run on old ones. Keep statements valid in
# both MySQL and SQLite.
MIGRATIONS: dict[str, dict[int, list[str]]] = {
    "amypo_schema.sql": {
        2: [
            "ALTER TABLE companies ADD COLUMN ctc_lpa DOUBLE",
            "ALTER TABLE company_criteria ADD COLUMN eligible_depts_json TEXT",
        ],
    },
}
_lock = threading.Lock()
_initialized: set[str] = set()


class DBConn:
    """Thin wrapper giving sqlite3 and PyMySQL connections the same execute/commit surface."""

    def __init__(self, raw: Any, backend: str) -> None:
        self.raw = raw
        self.backend = backend

    def execute(self, sql: str, params: tuple | list = ()) -> Any:
        if self.backend == "sqlite":
            return self.raw.execute(sql, params)
        cur = self.raw.cursor()
        cur.execute(sql.replace("?", "%s"), tuple(params) or None)
        return cur

    def executemany(self, sql: str, rows: list[tuple]) -> None:
        if self.backend == "sqlite":
            self.raw.executemany(sql, rows)
            return
        with self.raw.cursor() as cur:
            cur.executemany(sql.replace("?", "%s"), rows)

    def commit(self) -> None:
        self.raw.commit()

    def close(self) -> None:
        self.raw.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self.raw.commit()
            else:
                self.raw.rollback()
        finally:
            self.raw.close()


def _split_statements(schema_sql: str) -> list[str]:
    """Strip `--` comments and split on `;` (schema files contain no `;` inside literals)."""
    no_comments = re.sub(r"--[^\n]*", "", schema_sql)
    return [s.strip() for s in no_comments.split(";") if s.strip()]


def _apply_schema_once(key: str, conn: DBConn, schema_file: str) -> None:
    with _lock:
        if key in _initialized:
            return
        schema_sql = (_SCHEMA_DIR / conn.backend / schema_file).read_text(encoding="utf-8")
        if conn.backend == "sqlite":
            conn.raw.executescript(schema_sql)
        else:
            for stmt in _split_statements(schema_sql):
                conn.execute(stmt)
        _migrate(conn, schema_file)
        conn.commit()
        _initialized.add(key)


def _migrate(conn: DBConn, schema_file: str) -> None:
    steps = MIGRATIONS.get(schema_file, {})
    if not steps:
        return
    current = conn.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()["version"]
    for version in sorted(v for v in steps if v > current):
        for stmt in steps[version]:
            conn.execute(stmt)
        conn.execute("UPDATE schema_version SET version = ? WHERE id = 1", (version,))


# ---------- sqlite ----------

def _resolve_sqlite(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = Path(get_settings().db.sqlite.dir).expanduser() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect_sqlite(path_str: str, schema_file: str) -> DBConn:
    db_path = _resolve_sqlite(path_str)
    raw = sqlite3.connect(str(db_path), check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA journal_mode = WAL")
    raw.execute("PRAGMA foreign_keys = ON")
    conn = DBConn(raw, "sqlite")
    _apply_schema_once(f"sqlite:{db_path}", conn, schema_file)
    return conn


# ---------- mysql ----------

def _connect_mysql(database: str, schema_file: str) -> DBConn:
    import pymysql  # imported lazily so the sqlite-only test suite doesn't need it
    from pymysql.cursors import DictCursor

    cfg = get_settings().db.mysql
    common: dict[str, Any] = {
        "host": cfg.host,
        "port": cfg.port,
        "user": cfg.user,
        "password": cfg.password,
        "charset": "utf8mb4",
        "connect_timeout": cfg.connect_timeout_s,
        "cursorclass": DictCursor,
    }
    key = f"mysql:{cfg.host}:{cfg.port}/{database}"
    if key not in _initialized:
        # Create the database if the user is allowed to; otherwise it must already exist
        # (the compose MySQL container creates both via docker/mysql/init.sql).
        bootstrap = pymysql.connect(**common)
        try:
            with bootstrap.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        except pymysql.err.OperationalError:
            pass
        finally:
            bootstrap.close()
    conn = DBConn(pymysql.connect(database=database, **common), "mysql")
    _apply_schema_once(key, conn, schema_file)
    return conn


# ---------- public ----------

def get_ops_conn() -> DBConn:
    db = get_settings().db
    if db.backend == "sqlite":
        return _connect_sqlite(db.sqlite.ops_db_path, "ops_schema.sql")
    return _connect_mysql(db.mysql.ops_database, "ops_schema.sql")


def get_amypo_conn() -> DBConn:
    db = get_settings().db
    if db.backend == "sqlite":
        return _connect_sqlite(db.sqlite.amypo_db_path, "amypo_schema.sql")
    return _connect_mysql(db.mysql.amypo_database, "amypo_schema.sql")
