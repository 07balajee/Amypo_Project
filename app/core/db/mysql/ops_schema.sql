-- ops database (MySQL 8) — router + q&a operational logging. Applied idempotently on startup.
-- Kept column-for-column in sync with ../sqlite/ops_schema.sql (the test backend).
-- MySQL has no CREATE INDEX IF NOT EXISTS, so indexes are declared inline.

CREATE TABLE IF NOT EXISTS schema_version (
    id      INT PRIMARY KEY CHECK (id = 1),
    version INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
INSERT IGNORE INTO schema_version (id, version) VALUES (1, 1);

CREATE TABLE IF NOT EXISTS route_log (
    request_id      VARCHAR(128) PRIMARY KEY,
    ts              VARCHAR(40) NOT NULL,      -- ISO-8601 UTC string, same as the sqlite backend
    query           TEXT NOT NULL,
    complexity_hint VARCHAR(16),
    complexity      VARCHAR(16),
    complexity_prob DOUBLE,
    user_scope      VARCHAR(128),
    dry_run         TINYINT NOT NULL DEFAULT 0,
    routed_to       VARCHAR(32) NOT NULL,
    reasoning       TEXT NOT NULL,
    latency_ms      INT NOT NULL,
    estimated_cost  DOUBLE NOT NULL,
    tokens_in       INT,
    tokens_out      INT,
    cache_level     VARCHAR(16),
    replanned       TINYINT NOT NULL DEFAULT 0,
    candidates_json TEXT,
    snapshot_json   TEXT,
    INDEX idx_route_log_ts (ts),
    INDEX idx_route_log_routed_to (routed_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS qa_log (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts               VARCHAR(40) NOT NULL,
    user_id          VARCHAR(128),
    conversation_id  VARCHAR(128),
    question         TEXT NOT NULL,
    intent           VARCHAR(32),
    path             VARCHAR(16),
    answer           TEXT,
    confidence       DOUBLE,
    abstained        TINYINT NOT NULL DEFAULT 0,
    route_request_id VARCHAR(128),
    sources_json     TEXT,
    INDEX idx_qa_log_ts (ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quota_ledger (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts              VARCHAR(40) NOT NULL,
    request_id      VARCHAR(128),
    tier            VARCHAR(32) NOT NULL,
    units_consumed  DOUBLE NOT NULL,
    quota_remaining DOUBLE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cache_entry (
    cache_key     VARCHAR(255) PRIMARY KEY,
    scope         VARCHAR(128) NOT NULL,
    query         TEXT NOT NULL,
    response      MEDIUMTEXT NOT NULL,
    quality       INT NOT NULL,
    index_version VARCHAR(32) NOT NULL,
    created_at    VARCHAR(40) NOT NULL,
    expires_at    VARCHAR(40) NOT NULL,
    INDEX idx_cache_entry_scope (scope)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
