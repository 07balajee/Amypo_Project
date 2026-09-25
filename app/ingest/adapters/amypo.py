"""Adapter for the organiser (AMYPO) data. STUB until the real data arrives.

When the data is received:
  1. Implement the four methods below so they return the canonical shapes in `base.py`.
  2. Set `data.adapter: amypo` in config.yaml (or DATA__ADAPTER=amypo).
  3. Run `python -m app.ingest.cli --db-url mysql://...` to load it.
Nothing outside this file and config.yaml should need to change.

TODO mapping (fill in once the real files/schemas are known):
  documents        <- ?  syllabi / FAQ / policy files; doc_type must be one of base.DOC_TYPES
  students         <- ?  id, name, dept, year, cgpa, backlogs, coding_score, projects_count
  users            <- ?  user_id, role (student|staff), student_id
  courses          <- ?  code, title, dept, credits
  enrollments      <- ?  student_id, course_code, semester
  grades           <- ?  student_id, course_code, internal, external, total, grade
  attendance       <- ?  student_id, course_code, attendance_pct
  schedules        <- ?  course_code, session_type, day_or_date, start_time, end_time, room
  companies        <- ?  id, name, role, ctc_lpa (NULL if unknown)
  company_criteria <- ?  company_id, min_cgpa, max_backlogs, min_attendance, required_skills_json,
                         eligible_depts_json (NULL = all branches)
  skills, student_skills, module_skill_map <- ?
  past_queries     <- ?  optional; return [] if there is no query history
  benchmarks       <- the organiser harness, if it ships labelled sets; otherwise return {}
"""
from __future__ import annotations

from app.ingest.adapters.base import DataAdapter, Row, SourceDocument

_TODO = "AMYPO data not received yet; see the TODO mapping in app/ingest/adapters/amypo.py"


class AmypoAdapter(DataAdapter):
    name = "amypo"

    def load_documents(self) -> list[SourceDocument]:
        raise NotImplementedError(_TODO)

    def load_tables(self) -> dict[str, list[Row]]:
        raise NotImplementedError(_TODO)

    def load_past_queries(self) -> list[Row]:
        raise NotImplementedError(_TODO)

    def load_benchmarks(self) -> dict[str, list[Row]]:
        raise NotImplementedError(_TODO)
