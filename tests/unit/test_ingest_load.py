"""Loading synthetic data through the adapter into the (sqlite) amypo database."""
import pytest

from app.core import config as config_module
from app.core.db import conn as conn_module
from app.ingest.adapters import get_adapter
from app.ingest.adapters.amypo import AmypoAdapter
from app.ingest.loaders import load_all, record_exists


@pytest.fixture()
def amypo_conn(tmp_path, monkeypatch):
    monkeypatch.setenv("DB__BACKEND", "sqlite")
    monkeypatch.setenv("DB__SQLITE__DIR", str(tmp_path))
    config_module.get_settings(reload=True)
    conn_module._initialized.clear()
    with conn_module.get_amypo_conn() as conn:
        yield conn
    config_module.get_settings(reload=True)


def _count(conn, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]


def test_load_synthetic_into_db(amypo_conn):
    report = load_all(get_adapter("synthetic"), amypo_conn)
    assert report.dangling_record_ids == []
    assert report.index_version and report.index_version.startswith("v-")
    for table, n in {"students": 200, "courses": 8, "attendance": 1600, "router_prompts": 200}.items():
        assert _count(amypo_conn, table) == n
    assert _count(amypo_conn, "chunks") > _count(amypo_conn, "documents") == 15
    assert _count(amypo_conn, "qa_benchmark") >= 75


def test_reload_is_a_full_refresh(amypo_conn):
    adapter = get_adapter("synthetic")
    first = load_all(adapter, amypo_conn)
    second = load_all(adapter, amypo_conn)
    assert first.counts == second.counts
    assert _count(amypo_conn, "students") == 200


def test_record_ids_resolve(amypo_conn):
    load_all(get_adapter("synthetic"), amypo_conn)
    assert record_exists(amypo_conn, "attendance:S2023CS004:CS301")
    assert record_exists(amypo_conn, "module_skill_map:sk_sql:CS301 DBMS - Unit 3: SQL")  # ':' in value
    assert record_exists(amypo_conn, "faq#c0")
    assert not record_exists(amypo_conn, "students:S9999XX999")
    assert not record_exists(amypo_conn, "nosuchtable:1")


def test_edge_case_rows_in_db(amypo_conn):
    load_all(get_adapter("synthetic"), amypo_conn, parts=("tables",))
    row = amypo_conn.execute(
        "SELECT attendance_pct FROM attendance WHERE student_id = ? AND course_code = ?",
        ("S2023CS004", "CS301"),
    ).fetchone()
    assert row["attendance_pct"] == 74.9


def test_old_schema_is_migrated(tmp_path, monkeypatch):
    """A database created before schema v2 (no ctc_lpa / eligible_depts_json) is upgraded in place."""
    import sqlite3

    old = sqlite3.connect(tmp_path / "amypo.db")
    old.executescript(
        "CREATE TABLE schema_version (id INTEGER PRIMARY KEY, version INTEGER NOT NULL);"
        "INSERT INTO schema_version VALUES (1, 1);"
        "CREATE TABLE companies (id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL);"
        "CREATE TABLE company_criteria (company_id TEXT PRIMARY KEY, min_cgpa REAL NOT NULL,"
        " max_backlogs INTEGER NOT NULL, min_attendance REAL NOT NULL, required_skills_json TEXT NOT NULL);"
    )
    old.commit()
    old.close()
    monkeypatch.setenv("DB__BACKEND", "sqlite")
    monkeypatch.setenv("DB__SQLITE__DIR", str(tmp_path))
    config_module.get_settings(reload=True)
    conn_module._initialized.clear()
    with conn_module.get_amypo_conn() as conn:
        assert conn.execute("SELECT version FROM schema_version").fetchone()["version"] == 2
        load_all(get_adapter("synthetic"), conn, parts=("tables",))
        row = conn.execute("SELECT ctc_lpa FROM companies WHERE id = ?", ("amazon_sde",)).fetchone()
        assert row["ctc_lpa"] == 22.0
    config_module.get_settings(reload=True)


def test_amypo_adapter_is_a_stub():
    with pytest.raises(NotImplementedError):
        AmypoAdapter().load_tables()


def test_db_url_overrides_mysql_settings(monkeypatch):
    monkeypatch.setenv("DB__MYSQL__URL", "mysql://root:p%40ss@db.local:3310/amypo_x")
    m = config_module.get_settings(reload=True).db.mysql
    assert (m.host, m.port, m.user, m.password, m.amypo_database) == (
        "db.local", 3310, "root", "p@ss", "amypo_x")
    monkeypatch.delenv("DB__MYSQL__URL")
    config_module.get_settings(reload=True)
