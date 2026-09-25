"""Adapter interface: the ONLY place that knows where source data lives and what it looks like.

Everything downstream (loaders, retrieval, evaluation) consumes the canonical shapes defined here.
To plug in real data, write one adapter that returns these shapes (see `amypo.py`) and set
`data.adapter` in config.yaml; nothing else changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

# Canonical record tables and their columns, in parent-before-child (insert) order.
# Keys/columns match app/core/db/{mysql,sqlite}/amypo_schema.sql exactly.
TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "students": ("id", "name", "dept", "year", "cgpa", "backlogs", "coding_score", "projects_count"),
    "users": ("user_id", "role", "student_id"),
    "courses": ("code", "title", "dept", "credits"),
    "enrollments": ("student_id", "course_code", "semester"),
    "grades": ("student_id", "course_code", "internal", "external", "total", "grade"),
    "attendance": ("student_id", "course_code", "attendance_pct"),
    "schedules": ("course_code", "session_type", "day_or_date", "start_time", "end_time", "room"),
    "skills": ("id", "name"),
    "student_skills": ("student_id", "skill_id", "proficiency"),
    "companies": ("id", "name", "role", "ctc_lpa"),
    "company_criteria": (
        "company_id", "min_cgpa", "max_backlogs", "min_attendance", "required_skills_json",
        "eligible_depts_json",
    ),
    "module_skill_map": ("skill_id", "module", "weight"),
}

PAST_QUERY_COLUMNS: tuple[str, ...] = ("query_id", "cluster_id", "query", "answer", "record_id")

# Benchmark / training sets -> table columns.
BENCHMARK_COLUMNS: dict[str, tuple[str, ...]] = {
    "router_prompts": ("id", "query", "complexity_label", "hint", "category", "repeat_of"),
    "router_scenarios": ("prompt_id", "scenario", "t_sec", "optimal_route"),
    "qa_benchmark": (
        "id", "question", "user_id", "expected_answer", "gold_record_ids_json", "type", "expect",
    ),
}

DOC_TYPES = ("syllabus", "faq", "policy", "other")

Row = dict[str, Any]


@dataclass(frozen=True)
class SourceDocument:
    doc_id: str
    title: str
    doc_type: str  # one of DOC_TYPES
    source_path: str
    text: str  # already parsed to plain text / markdown


class DataAdapter(ABC):
    """Returns source data in canonical shapes. Implementations must not write to any database."""

    name: str = "base"

    @abstractmethod
    def load_documents(self) -> list[SourceDocument]:
        """Unstructured content (syllabi, FAQs, policies, ...), parsed to text."""

    @abstractmethod
    def load_tables(self) -> dict[str, list[Row]]:
        """Structured records keyed by table name; each row has exactly TABLE_COLUMNS[table]."""

    @abstractmethod
    def load_past_queries(self) -> list[Row]:
        """Previously answered questions (rows with PAST_QUERY_COLUMNS)."""

    @abstractmethod
    def load_benchmarks(self) -> dict[str, list[Row]]:
        """Training/evaluation sets keyed like BENCHMARK_COLUMNS. May return {} if none exist."""
