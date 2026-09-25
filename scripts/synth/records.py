"""Synthetic structured records for the amypo database (CLAUDE.md §9).

200 students across CS/IT/AD; every student takes all 8 courses. Placement edge cases are pinned on
S2023CS001..S2023CS007 against the Zoho SDE criteria (see EDGE_CASES). `eligibility()` and
`skill_gap()` are the reference implementations the benchmark answers are computed from; the Q&A
service's own implementation (M6) is tested against those answers.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass

from scripts.synth.content import COURSES

DEPT_BATCHES = [("CS", 2023, 60), ("CS", 2022, 40), ("IT", 2023, 40), ("IT", 2022, 20), ("AD", 2023, 40)]
DEPT_NAMES = {"CS": "Computer Science and Engineering", "IT": "Information Technology",
              "AD": "Artificial Intelligence and Data Science"}
YEAR_OF_STUDY = {2022: 4, 2023: 3}

FIRST = ["Aarav", "Aditi", "Akash", "Ananya", "Arjun", "Bhavya", "Deepak", "Divya", "Gokul", "Harini",
         "Ishaan", "Janani", "Karthik", "Kavya", "Lakshmi", "Madhan", "Meera", "Naveen", "Nisha", "Pradeep",
         "Priya", "Rahul", "Ramya", "Sanjay", "Sneha", "Surya", "Swathi", "Tarun", "Varsha", "Vikram",
         "Yamini", "Zara", "Abdul", "Fathima", "John", "Mary", "Rohan", "Sahana", "Vishnu", "Keerthana"]
LAST = ["Kumar", "Sharma", "Iyer", "Reddy", "Nair", "Menon", "Pillai", "Rao", "Das", "Patel", "Singh",
        "Krishnan", "Subramanian", "Raman", "Joseph", "Thomas", "Ali", "Khan", "Varma", "Bose"]

SKILLS = [
    ("sk_python", "Python"), ("sk_java", "Java"), ("sk_c", "C"), ("sk_cpp", "C++"), ("sk_sql", "SQL"),
    ("sk_dsa", "Data Structures and Algorithms"), ("sk_dbms", "DBMS Concepts"), ("sk_os", "Operating Systems"),
    ("sk_cn", "Computer Networks"), ("sk_oop", "Object-Oriented Programming"), ("sk_ml", "Machine Learning"),
    ("sk_dl", "Deep Learning"), ("sk_statistics", "Statistics"), ("sk_excel", "Excel"),
    ("sk_power_bi", "Power BI"), ("sk_tableau", "Tableau"), ("sk_html_css", "HTML and CSS"),
    ("sk_javascript", "JavaScript"), ("sk_react", "React"), ("sk_nodejs", "Node.js"), ("sk_django", "Django"),
    ("sk_spring", "Spring Boot"), ("sk_git", "Git"), ("sk_linux", "Linux"), ("sk_aws", "AWS"),
    ("sk_docker", "Docker"), ("sk_communication", "Communication"), ("sk_aptitude", "Quantitative Aptitude"),
    ("sk_system_design", "System Design"), ("sk_testing", "Software Testing"),
]
SKILL_NAME = dict(SKILLS)

CS, IT, AD = (DEPT_NAMES[d] for d in ("CS", "IT", "AD"))

# (id, name, role, ctc_lpa, min_cgpa, max_backlogs, min_attendance, {skill: min_proficiency},
#  eligible branches or None for all). CTC >= 10 LPA makes it a dream company (placement policy).
COMPANIES = [
    ("zoho_sde", "Zoho", "SDE", 8.4, 7.5, 0, 75.0, {"sk_dsa": 3, "sk_java": 3, "sk_sql": 2}, [CS, IT]),
    ("tcs_digital", "TCS", "Digital", 7.0, 6.5, 1, 75.0, {"sk_dsa": 2, "sk_python": 2, "sk_sql": 2}, None),
    ("infosys_da", "Infosys", "Data Analyst", 6.0, 6.0, 1, 75.0,
     {"sk_sql": 3, "sk_excel": 3, "sk_statistics": 2, "sk_power_bi": 2}, None),
    ("wipro_pe", "Wipro", "Project Engineer", 3.5, 6.0, 2, 70.0, {"sk_c": 2, "sk_oop": 2, "sk_aptitude": 2}, None),
    ("freshworks_fe", "Freshworks", "Frontend Developer", 12.0, 7.0, 0, 75.0,
     {"sk_html_css": 3, "sk_javascript": 3, "sk_react": 3}, [CS, IT]),
    ("accenture_ase", "Accenture", "Associate Software Engineer", 4.5, 6.5, 1, 75.0,
     {"sk_python": 2, "sk_oop": 2, "sk_communication": 3}, None),
    ("cognizant_genc", "Cognizant", "GenC Next", 6.75, 6.5, 0, 75.0, {"sk_java": 2, "sk_sql": 2, "sk_dsa": 2}, None),
    ("hcl_cloud", "HCLTech", "Cloud Engineer", 5.5, 6.5, 1, 75.0, {"sk_linux": 3, "sk_aws": 2, "sk_docker": 2}, None),
    ("musigma_ds", "Mu Sigma", "Decision Scientist", 6.5, 7.0, 0, 80.0,
     {"sk_statistics": 3, "sk_python": 3, "sk_ml": 2}, [CS, AD]),
    ("amazon_sde", "Amazon", "SDE", 22.0, 8.0, 0, 75.0, {"sk_dsa": 4, "sk_system_design": 3, "sk_java": 3}, None),
]

# Skills taught by course units -> module names used for skill-gap recommendations.
COURSE_MODULES = {
    "sk_sql": "CS301 DBMS - Unit 3: SQL", "sk_dbms": "CS301 DBMS - Unit 4: Normalization",
    "sk_os": "CS302 Operating Systems", "sk_cn": "CS303 Computer Networks",
    "sk_dsa": "CS304 DAA - Units 2-4", "sk_ml": "CS305 Machine Learning", "sk_statistics": "CS305 ML - Unit 5: Evaluation",
    "sk_html_css": "CS306 Web Tech - Unit 1: HTML and CSS", "sk_javascript": "CS306 Web Tech - Unit 2: JavaScript",
    "sk_react": "CS306 Web Tech - Unit 3: Front-end Frameworks", "sk_nodejs": "CS306 Web Tech - Unit 4: Server-side",
    "sk_python": "CS307 Python Programming", "sk_java": "CS308 Java Programming",
    "sk_oop": "CS308 Java - Unit 2: OOP", "sk_spring": "CS308 Java - Unit 5: Spring Boot",
}

# Skills most students of a department have (with at least basic proficiency); extras are random.
DEPT_CORE_SKILLS = {
    "CS": ["sk_dsa", "sk_java", "sk_python", "sk_sql", "sk_oop", "sk_c"],
    "IT": ["sk_python", "sk_sql", "sk_html_css", "sk_javascript", "sk_dsa", "sk_oop"],
    "AD": ["sk_python", "sk_statistics", "sk_ml", "sk_sql", "sk_excel", "sk_dsa"],
}

ZOHO = "zoho_sde"
# Edge cases pinned against the Zoho SDE criteria (CSE/IT only, min_cgpa 7.5, max_backlogs 0,
# attendance 75, dsa>=3, java>=3, sql>=2). Each dict overrides the random profile.
EDGE_CASES: dict[str, dict] = {
    "S2023CS001": {"note": "exactly at every Zoho threshold -> eligible",
                   "cgpa": 7.5, "backlogs": 0, "attendance": 75.0, "skills": {"sk_dsa": 3, "sk_java": 3, "sk_sql": 2, "sk_python": 2}},
    "S2023CS002": {"note": "one backlog over the Zoho limit -> not eligible (eligible for TCS Digital)",
                   "cgpa": 7.5, "backlogs": 1, "attendance": 75.0, "skills": {"sk_dsa": 3, "sk_java": 3, "sk_sql": 2, "sk_python": 2}},
    "S2023CS003": {"note": "missing required skill Java -> not eligible",
                   "cgpa": 8.1, "backlogs": 0, "attendance": 88.0, "skills": {"sk_dsa": 4, "sk_sql": 3, "sk_python": 3}},
    "S2023CS004": {"note": "74.9% attendance -> not eligible, and in the condonation band",
                   "cgpa": 7.9, "backlogs": 0, "attendance": 74.9, "skills": {"sk_dsa": 3, "sk_java": 4, "sk_sql": 3}},
    "S2023CS005": {"note": "CGPA 7.49, just below 7.5 -> not eligible",
                   "cgpa": 7.49, "backlogs": 0, "attendance": 90.0, "skills": {"sk_dsa": 4, "sk_java": 4, "sk_sql": 4}},
    "S2023CS006": {"note": "DSA proficiency 2 < required 3 -> not eligible",
                   "cgpa": 8.4, "backlogs": 0, "attendance": 92.0, "skills": {"sk_dsa": 2, "sk_java": 4, "sk_sql": 3}},
    "S2023AD001": {"note": "AI&DS branch, otherwise strong -> not eligible for Zoho (CSE/IT only)",
                   "cgpa": 8.6, "backlogs": 0, "attendance": 91.0, "skills": {"sk_dsa": 4, "sk_java": 4, "sk_sql": 4, "sk_python": 4}},
    "S2023CS007": {"note": "64.9% attendance in CS302 -> below condonation, not permitted to write the exam",
                   "cgpa": 6.9, "backlogs": 0, "attendance": 82.0, "attendance_override": {"CS302": 64.9},
                   "skills": {"sk_c": 3, "sk_python": 2, "sk_oop": 2}},
}

GRADE_BANDS = [(91, "O", 10), (81, "A+", 9), (71, "A", 8), (61, "B+", 7), (56, "B", 6), (50, "C", 5), (0, "U", 0)]
STAFF = [("staff_placement", "placement officer"), ("staff_hod_cs", "head of department, CSE"),
         ("staff_exam_cell", "exam cell")]

EXAM_DATES = {"CS301": "2025-11-24", "CS302": "2025-11-26", "CS303": "2025-11-28", "CS304": "2025-12-01",
              "CS305": "2026-04-20", "CS306": "2026-04-22", "CS307": "2026-04-24", "CS308": "2026-04-27"}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SLOTS = [("09:00", "09:50"), ("10:00", "10:50"), ("11:10", "12:00"), ("13:30", "14:20"), ("14:30", "15:20")]


def grade_for(total: float) -> tuple[str, int]:
    for floor, letter, points in GRADE_BANDS:
        if total >= floor:
            return letter, points
    return "U", 0


@dataclass
class Records:
    tables: dict[str, list[dict]]
    edge_cases: dict[str, str]  # student id -> why it is an edge case


def _student_ids() -> list[tuple[str, str, int]]:
    out = []
    for dept, batch, n in DEPT_BATCHES:
        out += [(f"S{batch}{dept}{i:03d}", dept, batch) for i in range(1, n + 1)]
    return out


def _marks(rng: random.Random, cgpa: float, fail: bool) -> tuple[float, float, float]:
    if fail:
        internal = rng.randint(14, 26)
        external = rng.randint(12, 29)  # < 30/60 -> fails the external minimum
    else:
        target = min(99, max(52, round(cgpa * 10 - 4 + rng.gauss(0, 7))))
        internal = min(40, max(22, round(target * 0.4 + rng.gauss(0, 2.5))))
        external = min(60, max(30, target - internal))
    return float(internal), float(external), float(internal + external)


def build(seed: int) -> Records:
    rng = random.Random(seed)
    students, users, enrollments, grades, attendance, student_skills = [], [], [], [], [], []

    for sid, dept, batch in _student_ids():
        edge = EDGE_CASES.get(sid)
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        cgpa = round(min(9.8, max(5.2, rng.gauss(7.3, 0.9))), 2)
        backlogs = rng.choices([0, 1, 2, 3], weights=[80, 12, 6, 2])[0]
        coding = round(min(100, max(10, rng.gauss(60, 16))), 1)
        projects = rng.randint(0, 6)
        base_att = min(99.0, max(66.0, rng.gauss(84, 7)))
        if edge:
            cgpa, backlogs = edge["cgpa"], edge["backlogs"]
            if cgpa >= 8.0:
                coding, projects = max(coding, 75.0), max(projects, 3)

        students.append({"id": sid, "name": name, "dept": DEPT_NAMES[dept], "year": YEAR_OF_STUDY[batch],
                         "cgpa": cgpa, "backlogs": backlogs, "coding_score": coding, "projects_count": projects})
        users.append({"user_id": sid, "role": "student", "student_id": sid})

        failed = set(rng.sample([c["code"] for c in COURSES], backlogs))
        for c in COURSES:
            code = c["code"]
            enrollments.append({"student_id": sid, "course_code": code, "semester": c["semester"]})
            internal, external, total = _marks(rng, cgpa, code in failed)
            # Below 30/60 in the external exam is a fail (grade U) whatever the total (exam policy).
            letter = "U" if external < 30 else grade_for(total)[0]
            grades.append({"student_id": sid, "course_code": code, "internal": internal,
                           "external": external, "total": total, "grade": letter})
            if edge:
                pct = edge.get("attendance_override", {}).get(code, edge["attendance"])
            else:
                pct = round(min(100.0, max(60.0, base_att + rng.gauss(0, 4))), 1)
            attendance.append({"student_id": sid, "course_code": code, "attendance_pct": pct})

        if edge:
            owned = dict(edge["skills"])
        else:
            core = [s for s in DEPT_CORE_SKILLS[dept] if rng.random() < 0.85]
            extras = rng.sample([s for s, _ in SKILLS if s not in DEPT_CORE_SKILLS[dept]], rng.randint(2, 6))
            owned = {s: rng.choices([1, 2, 3, 4, 5], weights=[5, 20, 40, 25, 10])[0] for s in core}
            owned |= {s: rng.choices([1, 2, 3, 4, 5], weights=[15, 30, 30, 18, 7])[0] for s in extras}
        for skill_id in sorted(owned):
            student_skills.append({"student_id": sid, "skill_id": skill_id, "proficiency": owned[skill_id]})

    users += [{"user_id": uid, "role": "staff", "student_id": None} for uid, _ in STAFF]

    courses = [{"code": c["code"], "title": c["title"], "dept": DEPT_NAMES["CS"], "credits": c["credits"]}
               for c in COURSES]

    schedules = []
    for i, c in enumerate(COURSES):
        code = c["code"]
        for k in range(3):
            day = DAYS[(i + 2 * k) % 5]
            start, end = SLOTS[(i + k) % len(SLOTS)]
            schedules.append({"course_code": code, "session_type": "lecture", "day_or_date": day,
                              "start_time": start, "end_time": end, "room": f"LH-{101 + i}"})
        if c["lab"]:
            schedules.append({"course_code": code, "session_type": "lab", "day_or_date": DAYS[(i + 1) % 5],
                              "start_time": "13:30", "end_time": "16:10", "room": f"LAB-{1 + i % 4}"})
        schedules.append({"course_code": code, "session_type": "exam", "day_or_date": EXAM_DATES[code],
                          "start_time": "09:30", "end_time": "12:30", "room": "Exam Hall A"})

    companies, criteria = [], []
    for cid, name, role, ctc, min_cgpa, max_bl, min_att, req, depts in COMPANIES:
        companies.append({"id": cid, "name": name, "role": role, "ctc_lpa": ctc})
        criteria.append({
            "company_id": cid, "min_cgpa": min_cgpa, "max_backlogs": max_bl, "min_attendance": min_att,
            "required_skills_json": json.dumps(
                [{"skill_id": s, "min_proficiency": p} for s, p in req.items()], separators=(",", ":")),
            "eligible_depts_json": json.dumps(depts) if depts else None,
        })

    module_map = []
    for skill_id, skill_name in SKILLS:
        mods = []
        if skill_id in COURSE_MODULES:
            mods.append((COURSE_MODULES[skill_id], 1.0))
        mods.append((f"AMYPO {skill_name} Bootcamp (2 weeks)", 0.8))
        mods.append((f"AMYPO {skill_name} Practice Track", 0.5))
        module_map += [{"skill_id": skill_id, "module": m, "weight": w} for m, w in mods]

    tables = {
        "students": students, "users": users, "courses": courses, "enrollments": enrollments,
        "grades": grades, "attendance": attendance, "schedules": schedules,
        "skills": [{"id": s, "name": n} for s, n in SKILLS], "student_skills": student_skills,
        "companies": companies, "company_criteria": criteria, "module_skill_map": module_map,
    }
    return Records(tables=tables, edge_cases={k: v["note"] for k, v in EDGE_CASES.items()})


# ---------------------------------------------------------------- reference placement logic

def _index(rec: Records):
    t = rec.tables
    students = {s["id"]: s for s in t["students"]}
    att: dict[str, list[float]] = {}
    for a in t["attendance"]:
        att.setdefault(a["student_id"], []).append(a["attendance_pct"])
    skills: dict[str, dict[str, int]] = {}
    for s in t["student_skills"]:
        skills.setdefault(s["student_id"], {})[s["skill_id"]] = s["proficiency"]
    crit = {c["company_id"]: c for c in t["company_criteria"]}
    return students, att, skills, crit


def avg_attendance(rec: Records, sid: str) -> float:
    _, att, _, _ = _index(rec)
    return round(sum(att[sid]) / len(att[sid]), 2)


def eligibility(rec: Records, sid: str, company_id: str) -> tuple[bool, list[str]]:
    """-> (eligible, failed criteria as human-readable strings)."""
    students, att, skills, crit = _index(rec)
    s, c = students[sid], crit[company_id]
    fails = []
    if c["eligible_depts_json"] and s["dept"] not in json.loads(c["eligible_depts_json"]):
        fails.append(f"branch {s['dept']} not in eligible branches")
    if s["cgpa"] < c["min_cgpa"]:
        fails.append(f"CGPA {s['cgpa']} < {c['min_cgpa']}")
    if s["backlogs"] > c["max_backlogs"]:
        fails.append(f"backlogs {s['backlogs']} > {c['max_backlogs']}")
    avg = round(sum(att[sid]) / len(att[sid]), 2)
    if avg < c["min_attendance"]:
        fails.append(f"attendance {avg}% < {c['min_attendance']}%")
    for req in json.loads(c["required_skills_json"]):
        have = skills.get(sid, {}).get(req["skill_id"], 0)
        if have < req["min_proficiency"]:
            fails.append(f"{SKILL_NAME[req['skill_id']]} proficiency {have} < {req['min_proficiency']}")
    return (not fails), fails


def skill_gap(rec: Records, sid: str, company_id: str) -> list[tuple[str, int, int, str]]:
    """-> [(skill_id, have, need, top module)] for each required skill the student falls short on."""
    _, _, skills, crit = _index(rec)
    modules: dict[str, list[tuple[float, str]]] = {}
    for m in rec.tables["module_skill_map"]:
        modules.setdefault(m["skill_id"], []).append((m["weight"], m["module"]))
    gaps = []
    for req in json.loads(crit[company_id]["required_skills_json"]):
        have = skills.get(sid, {}).get(req["skill_id"], 0)
        if have < req["min_proficiency"]:
            top = max(modules[req["skill_id"]])[1]
            gaps.append((req["skill_id"], have, req["min_proficiency"], top))
    return gaps
