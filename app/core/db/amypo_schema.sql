-- amypo.db — documents/chunks + structured academic/placement records. Applied idempotently.
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);
INSERT OR IGNORE INTO schema_version (id, version) VALUES (1, 1);

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
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS company_criteria (
    company_id TEXT PRIMARY KEY REFERENCES companies(id),
    min_cgpa       REAL NOT NULL,
    max_backlogs   INTEGER NOT NULL,
    min_attendance REAL NOT NULL,
    required_skills_json TEXT NOT NULL  -- [{"skill_id": "...", "min_proficiency": N}, ...]
);

CREATE TABLE IF NOT EXISTS module_skill_map (
    skill_id TEXT NOT NULL REFERENCES skills(id),
    module   TEXT NOT NULL,
    weight   REAL NOT NULL,
    PRIMARY KEY (skill_id, module)
);
