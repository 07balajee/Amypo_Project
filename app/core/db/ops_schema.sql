-- ops.db — router + q&a operational logging. Applied idempotently on startup.
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);
INSERT OR IGNORE INTO schema_version (id, version) VALUES (1, 1);

CREATE TABLE IF NOT EXISTS route_log (
    request_id      TEXT PRIMARY KEY,
    ts              TEXT NOT NULL,
    query           TEXT NOT NULL,
    complexity_hint TEXT,
    complexity      TEXT,
    complexity_prob REAL,
    user_scope      TEXT,
    dry_run         INTEGER NOT NULL DEFAULT 0,
    routed_to       TEXT NOT NULL,
    reasoning       TEXT NOT NULL,
    latency_ms      INTEGER NOT NULL,
    estimated_cost  REAL NOT NULL,
    tokens_in       INTEGER,
    tokens_out      INTEGER,
    cache_level     TEXT,
    replanned       INTEGER NOT NULL DEFAULT 0,
    candidates_json TEXT,
    snapshot_json   TEXT
);
CREATE INDEX IF NOT EXISTS idx_route_log_ts ON route_log (ts);
CREATE INDEX IF NOT EXISTS idx_route_log_routed_to ON route_log (routed_to);

CREATE TABLE IF NOT EXISTS qa_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    user_id         TEXT,
    conversation_id TEXT,
    question        TEXT NOT NULL,
    intent          TEXT,
    path            TEXT,
    answer          TEXT,
    confidence      REAL,
    abstained       INTEGER NOT NULL DEFAULT 0,
    route_request_id TEXT,
    sources_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_qa_log_ts ON qa_log (ts);

CREATE TABLE IF NOT EXISTS quota_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    request_id      TEXT,
    tier            TEXT NOT NULL,
    units_consumed  REAL NOT NULL,
    quota_remaining REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS cache_entry (
    cache_key   TEXT PRIMARY KEY,
    scope       TEXT NOT NULL,
    query       TEXT NOT NULL,
    response    TEXT NOT NULL,
    quality     INTEGER NOT NULL,
    index_version TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cache_entry_scope ON cache_entry (scope);
