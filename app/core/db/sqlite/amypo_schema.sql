-- amypo.db — documents/chunks + structured academic/placement records. Applied idempotently.
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);
-- Fresh databases start at the latest version; older ones are upgraded by conn.py MIGRATIONS.
INSERT OR IGNORE INTO schema_version (id, version) VALUES (1, 2);

-- ---------- documents / chunks (RAG) ----------
CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    doc_type    TEXT NOT NULL,      -- syllabus|faq|policy|other
    source_path TEXT NOT NULL,
    index_version TEXT NOT NULL DEFAULT 'v1'
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id    TEXT PRIMARY KEY,   -- doc_id#c{n}
    doc_id      TEXT NOT NULL REFERENCES documents(doc_id),
    ordinal     INTEGER NOT NULL,
    text        TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    index_version TEXT NOT NULL DEFAULT 'v1'
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks (doc_id);

-- ---------- users / access control ----------
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    role    TEXT NOT NULL CHECK (role IN ('student', 'staff')),
    student_id TEXT
);

-- ---------- academic records ----------
CREATE TABLE IF NOT EXISTS students (
    id             TEXT PRIMARY KEY,  -- e.g. S2023CS041
    name           TEXT NOT NULL,
    dept           TEXT NOT NULL,
    year           INTEGER NOT NULL,
    cgpa           REAL NOT NULL,
    backlogs       INTEGER NOT NULL,
    coding_score   REAL NOT NULL,
    projects_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    code   TEXT PRIMARY KEY,   -- e.g. CS301
    title  TEXT NOT NULL,
    dept   TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    student_id TEXT NOT NULL REFERENCES students(id),
    course_code TEXT NOT NULL REFERENCES courses(code),
    semester    TEXT NOT NULL,
    PRIMARY KEY (student_id, course_code, semester)
);

CREATE TABLE IF NOT EXISTS grades (
    student_id  TEXT NOT NULL REFERENCES students(id),
    course_code TEXT NOT NULL REFERENCES courses(code),
    internal    REAL,
    external    REAL,
    total       REAL,
    grade       TEXT,
    PRIMARY KEY (student_id, course_code)
);

CREATE TABLE IF NOT EXISTS attendance (
    student_id  TEXT NOT NULL REFERENCES students(id),
    course_code TEXT NOT NULL REFERENCES courses(code),
    attendance_pct REAL NOT NULL,
    PRIMARY KEY (student_id, course_code)
);

CREATE TABLE IF NOT EXISTS schedules (
    course_code TEXT NOT NULL REFERENCES courses(code),
    session_type TEXT NOT NULL,   -- lecture|lab|exam
    day_or_date  TEXT NOT NULL,
    start_time   TEXT,
    end_time     TEXT,
    room         TEXT
);

CREATE TABLE IF NOT EXISTS skills (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS student_skills (
    student_id TEXT NOT NULL REFERENCES students(id),
    skill_id   TEXT NOT NULL REFERENCES skills(id),
    proficiency INTEGER NOT NULL CHECK (proficiency BETWEEN 0 AND 5),
    PRIMARY KEY (student_id, skill_id)
);

-- ---------- placement ----------
CREATE TABLE IF NOT EXISTS companies (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    ctc_lpa REAL             -- offered CTC in lakhs per annum; >= 10 is a dream company
);

CREATE TABLE IF NOT EXISTS company_criteria (
    company_id TEXT PRIMARY KEY REFERENCES companies(id),
    min_cgpa       REAL NOT NULL,
    max_backlogs   INTEGER NOT NULL,
    min_attendance REAL NOT NULL,
    required_skills_json TEXT NOT NULL, -- [{"skill_id": "...", "min_proficiency": N}, ...]
    eligible_depts_json TEXT             -- ["Computer Science and Engineering", ...]; NULL = all branches
);

CREATE TABLE IF NOT EXISTS module_skill_map (
    skill_id TEXT NOT NULL REFERENCES skills(id),
    module   TEXT NOT NULL,
    weight   REAL NOT NULL,
    PRIMARY KEY (skill_id, module)
);

-- ---------- training / evaluation sets (loaded from the adapter's load_past_queries/benchmarks) ----------
CREATE TABLE IF NOT EXISTS past_queries (
    query_id   TEXT PRIMARY KEY,
    cluster_id TEXT NOT NULL,        -- paraphrases of one question share a cluster
    query      TEXT NOT NULL,
    answer     TEXT NOT NULL,
    record_id  TEXT NOT NULL         -- chunk the answer comes from (doc_id#c{n})
);
CREATE INDEX IF NOT EXISTS idx_past_queries_cluster ON past_queries (cluster_id);

CREATE TABLE IF NOT EXISTS router_prompts (
    id               TEXT PRIMARY KEY,
    query            TEXT NOT NULL,
    complexity_label TEXT NOT NULL,  -- low|medium|high (ground truth)
    hint             TEXT,           -- sometimes wrong on purpose
    category         TEXT NOT NULL,  -- definition|code|math|essay|...
    repeat_of        TEXT            -- set for paraphrases of an earlier prompt
);

CREATE TABLE IF NOT EXISTS router_scenarios (
    prompt_id     TEXT NOT NULL,
    scenario      TEXT NOT NULL,
    t_sec         INTEGER NOT NULL,
    optimal_route TEXT NOT NULL,
    PRIMARY KEY (prompt_id, scenario, t_sec)
);

CREATE TABLE IF NOT EXISTS qa_benchmark (
    id                   TEXT PRIMARY KEY,
    question             TEXT NOT NULL,
    user_id              TEXT,
    expected_answer      TEXT NOT NULL,
    gold_record_ids_json TEXT NOT NULL,     -- JSON array of record_ids
    type                 TEXT NOT NULL,     -- knowledge|record|eligibility|skill_gap|unanswerable
    expect               TEXT NOT NULL      -- answer|abstain|refuse
);
