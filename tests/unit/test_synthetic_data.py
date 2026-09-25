"""M1 acceptance: synthetic data is reproducible, the committed copy is current, and the row counts
and edge cases from CLAUDE.md §9 hold."""
import json
from pathlib import Path

import pytest

from scripts.gen_synthetic import REPO_ROOT, generate
from scripts.synth import records

COMMITTED = REPO_ROOT / "data" / "synthetic"
TEXT_SUFFIXES = {".csv", ".jsonl", ".md", ".yaml"}


@pytest.fixture(scope="module")
def fresh(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("synthetic")
    generate(out)
    return out


def _files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_generation_is_deterministic(fresh, tmp_path):
    generate(tmp_path)
    assert _files(tmp_path) == _files(fresh)


def test_committed_data_matches_generator(fresh):
    """Fails if the generator changed but data/synthetic wasn't regenerated.
    Binary PDF/DOCX are skipped: their bytes can differ across library versions."""
    new = {k: v for k, v in _files(fresh).items() if Path(k).suffix in TEXT_SUFFIXES}
    old = {k: v for k, v in _files(COMMITTED).items() if Path(k).suffix in TEXT_SUFFIXES}
    assert old == new, "run `python scripts/gen_synthetic.py` and commit data/synthetic"


def _jsonl(root: Path, name: str) -> list[dict]:
    return [json.loads(line) for line in (root / name).read_text(encoding="utf-8").splitlines()]


def test_row_counts(fresh):
    rec = records.build(20260101)
    t = rec.tables
    assert len(t["students"]) == 200
    assert len(t["courses"]) == 8
    assert len(t["skills"]) == 30
    assert len(t["companies"]) == 10
    assert len(t["attendance"]) == len(t["grades"]) == 200 * 8
    assert len(_jsonl(fresh, "router_prompts.jsonl")) == 200
    assert 250 <= len((fresh / "past_queries.csv").read_text(encoding="utf-8").splitlines()) - 1 <= 320
    assert len(list((fresh / "scenarios").glob("*.csv"))) == 6
    manifest = (fresh / "docs" / "manifest.yaml").read_text(encoding="utf-8")
    assert {".md", ".pdf", ".docx"} <= {p.suffix for p in (fresh / "docs").iterdir()}
    assert "notice_hostel_w32" in manifest


def test_backlogs_match_u_grades():
    t = records.build(20260101).tables
    u = {}
    for g in t["grades"]:
        u[g["student_id"]] = u.get(g["student_id"], 0) + (g["grade"] == "U")
    assert all(s["backlogs"] == u[s["id"]] for s in t["students"])


@pytest.mark.parametrize(
    ("sid", "company", "eligible", "reason"),
    [
        ("S2023CS001", "zoho_sde", True, None),
        ("S2023CS002", "zoho_sde", False, "backlogs 1 > 0"),
        ("S2023CS002", "tcs_digital", True, None),
        ("S2023CS003", "zoho_sde", False, "Java proficiency 0 < 3"),
        ("S2023CS004", "zoho_sde", False, "attendance 74.9% < 75.0%"),
        ("S2023CS005", "zoho_sde", False, "CGPA 7.49 < 7.5"),
        ("S2023CS006", "zoho_sde", False, "Data Structures and Algorithms proficiency 2 < 3"),
        ("S2023AD001", "zoho_sde", False,
         "branch Artificial Intelligence and Data Science not in eligible branches"),
    ],
)
def test_placement_edge_cases(sid, company, eligible, reason):
    rec = records.build(20260101)
    ok, fails = records.eligibility(rec, sid, company)
    assert ok is eligible
    if reason:
        assert fails == [reason]


def test_attendance_edge_cases():
    att = {(a["student_id"], a["course_code"]): a["attendance_pct"]
           for a in records.build(20260101).tables["attendance"]}
    assert att[("S2023CS004", "CS301")] == 74.9  # condonation band
    assert att[("S2023CS007", "CS302")] == 64.9  # below condonation
    assert att[("S2023CS001", "CS301")] == 75.0  # exactly at the threshold


def test_qa_benchmark_mix(fresh):
    qa = _jsonl(fresh, "qa_benchmark.jsonl")
    assert 75 <= len(qa) <= 90
    assert sum(q["type"] == "unanswerable" for q in qa) / len(qa) >= 0.15
    assert sum(q["expect"] == "refuse" for q in qa) / len(qa) >= 0.10
    assert all(q["gold_record_ids"] for q in qa if q["expect"] == "answer")
    assert all(not q["gold_record_ids"] for q in qa if q["expect"] != "answer")


def test_router_labels_cover_every_route(fresh):
    labels = {r["optimal_route"] for r in _jsonl(fresh, "router_scenarios.jsonl")}
    assert labels == {"local_model", "cloud_api", "offline_fallback"}
    prompts = _jsonl(fresh, "router_prompts.jsonl")
    assert any(p["hint"] not in (None, p["complexity_label"]) for p in prompts)  # wrong hints exist
    assert any(p["repeat_of"] for p in prompts)
