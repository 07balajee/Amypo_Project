-- amypo database (MySQL 8) — documents/chunks + structured academic/placement records.
-- Applied idempotently. Kept column-for-column in sync with ../sqlite/amypo_schema.sql.
-- MySQL has no CREATE INDEX IF NOT EXISTS, so indexes are declared inline.

CREATE TABLE IF NOT EXISTS schema_version (
    id      INT PRIMARY KEY CHECK (id = 1),
    version INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- Fresh databases start at the latest version; older ones are upgraded by conn.py MIGRATIONS.
INSERT IGNORE INTO schema_version (id, version) VALUES (1, 2);

-- ---------- documents / chunks (RAG) ----------
CREATE TABLE IF NOT EXISTS documents (
    doc_id        VARCHAR(128) PRIMARY KEY,
    title         VARCHAR(512) NOT NULL,
    doc_type      VARCHAR(32) NOT NULL,     -- syllabus|faq|policy|other
    source_path   VARCHAR(1024) NOT NULL,
    index_version VARCHAR(32) NOT NULL DEFAULT 'v1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id      VARCHAR(160) PRIMARY KEY, -- doc_id#c{n}
    doc_id        VARCHAR(128) NOT NULL,
    ordinal       INT NOT NULL,
    text          MEDIUMTEXT NOT NULL,
    token_count   INT NOT NULL,
    index_version VARCHAR(32) NOT NULL DEFAULT 'v1',
    INDEX idx_chunks_doc_id (doc_id),
    FOREIGN KEY (doc_id) REFERENCES documents (doc_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- academic records ----------
CREATE TABLE IF NOT EXISTS students (
    id             VARCHAR(32) PRIMARY KEY,  -- e.g. S2023CS041
    name           VARCHAR(255) NOT NULL,
    dept           VARCHAR(64) NOT NULL,
    year           INT NOT NULL,
    cgpa           DOUBLE NOT NULL,
    backlogs       INT NOT NULL,
    coding_score   DOUBLE NOT NULL,
    projects_count INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- users / access control ----------
CREATE TABLE IF NOT EXISTS users (
    user_id    VARCHAR(128) PRIMARY KEY,
    role       VARCHAR(16) NOT NULL CHECK (role IN ('student', 'staff')),
    student_id VARCHAR(32)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS courses (
    code    VARCHAR(16) PRIMARY KEY,   -- e.g. CS301
    title   VARCHAR(255) NOT NULL,
    dept    VARCHAR(64) NOT NULL,
    credits INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS enrollments (
    student_id  VARCHAR(32) NOT NULL,
    course_code VARCHAR(16) NOT NULL,
    semester    VARCHAR(16) NOT NULL,
    PRIMARY KEY (student_id, course_code, semester),
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (course_code) REFERENCES courses (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS grades (
    student_id  VARCHAR(32) NOT NULL,
    course_code VARCHAR(16) NOT NULL,
    internal    DOUBLE,
    external    DOUBLE,
    total       DOUBLE,
    grade       VARCHAR(4),
    PRIMARY KEY (student_id, course_code),
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (course_code) REFERENCES courses (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance (
    student_id     VARCHAR(32) NOT NULL,
    course_code    VARCHAR(16) NOT NULL,
    attendance_pct DOUBLE NOT NULL,
    PRIMARY KEY (student_id, course_code),
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (course_code) REFERENCES courses (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedules (
    course_code  VARCHAR(16) NOT NULL,
    session_type VARCHAR(16) NOT NULL,   -- lecture|lab|exam
    day_or_date  VARCHAR(32) NOT NULL,
    start_time   VARCHAR(8),
    end_time     VARCHAR(8),
    room         VARCHAR(32),
    FOREIGN KEY (course_code) REFERENCES courses (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS skills (
    id   VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_skills (
    student_id  VARCHAR(32) NOT NULL,
    skill_id    VARCHAR(64) NOT NULL,
    proficiency INT NOT NULL CHECK (proficiency BETWEEN 0 AND 5),
    PRIMARY KEY (student_id, skill_id),
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (skill_id) REFERENCES skills (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- placement ----------
CREATE TABLE IF NOT EXISTS companies (
    id   VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    role VARCHAR(128) NOT NULL,
    ctc_lpa DOUBLE                         -- offered CTC in lakhs per annum; >= 10 is a dream company
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_criteria (
    company_id           VARCHAR(64) PRIMARY KEY,
    min_cgpa             DOUBLE NOT NULL,
    max_backlogs         INT NOT NULL,
    min_attendance       DOUBLE NOT NULL,
    required_skills_json TEXT NOT NULL,  -- [{"skill_id": "...", "min_proficiency": N}, ...]
    eligible_depts_json  TEXT,           -- ["Computer Science and Engineering", ...]; NULL = all branches
    FOREIGN KEY (company_id) REFERENCES companies (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS module_skill_map (
    skill_id VARCHAR(64) NOT NULL,
    module   VARCHAR(128) NOT NULL,
    weight   DOUBLE NOT NULL,
    PRIMARY KEY (skill_id, module),
    FOREIGN KEY (skill_id) REFERENCES skills (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- training / evaluation sets (loaded from the adapter's load_past_queries/benchmarks) ----------
CREATE TABLE IF NOT EXISTS past_queries (
    query_id   VARCHAR(32) PRIMARY KEY,
    cluster_id VARCHAR(32) NOT NULL,        -- paraphrases of one question share a cluster
    query      TEXT NOT NULL,
    answer     TEXT NOT NULL,
    record_id  VARCHAR(160) NOT NULL,       -- chunk the answer comes from (doc_id#c{n})
    INDEX idx_past_queries_cluster (cluster_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS router_prompts (
    id               VARCHAR(32) PRIMARY KEY,
    query            TEXT NOT NULL,
    complexity_label VARCHAR(16) NOT NULL,  -- low|medium|high (ground truth)
    hint             VARCHAR(16),           -- sometimes wrong on purpose
    category         VARCHAR(32) NOT NULL,  -- definition|code|math|essay|...
    repeat_of        VARCHAR(32)            -- set for paraphrases of an earlier prompt
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS router_scenarios (
    prompt_id     VARCHAR(32) NOT NULL,
    scenario      VARCHAR(32) NOT NULL,
    t_sec         INT NOT NULL,
    optimal_route VARCHAR(32) NOT NULL,
    PRIMARY KEY (prompt_id, scenario, t_sec)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS qa_benchmark (
    id                   VARCHAR(32) PRIMARY KEY,
    question             TEXT NOT NULL,
    user_id              VARCHAR(128),
    expected_answer      TEXT NOT NULL,
    gold_record_ids_json TEXT NOT NULL,     -- JSON array of record_ids
    type                 VARCHAR(16) NOT NULL,  -- knowledge|record|eligibility|skill_gap|unanswerable
    expect               VARCHAR(16) NOT NULL   -- answer|abstain|refuse
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
