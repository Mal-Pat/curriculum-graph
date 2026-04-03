import json
import re
from collections import Counter
from pathlib import Path

from yfiles_graphs_for_streamlit import Edge, Node


DATA_DIR = Path("data")
DEFAULT_COURSES_PATH = Path("IISER-P/all_courses.json")
DEFAULT_MAJOR_MINOR_PATH = Path("IISER-P/major_minor_requirements.json")

COURSE_KIND_COLOR_MAP = {
    "normal": "#1f7a8c",
    "lab": "#2a9d8f",
    "semester_project": "#e9c46a",
}

SET_COLOR_MAP = {
    "set_d": "#d1495b",  # compulsory
    "set_a": "#0077b6",  # minimum required from pool
    "set_b": "#f4a261",  # capped pool
    "set_c": "#2a9d8f",  # supplementary
    "set_e": "#8d99ae",  # excluded / not counted
    "support": "#6c757d",  # added prerequisite support nodes
}


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_courses(courses_relative: Path | None = None):
    relative = courses_relative or DEFAULT_COURSES_PATH
    payload = load_json(DATA_DIR / relative)
    return payload.get("all_courses", [])


def load_programs(programs_relative: Path | None = None):
    relative = programs_relative or DEFAULT_MAJOR_MINOR_PATH
    payload = load_json(DATA_DIR / relative)
    return normalize_programs(payload)


def normalize_programs(payload):
    if isinstance(payload, list):
        return payload
    return payload.get("major_minor_requirements", [])


def program_key(criteria):
    meta = criteria.get("program_metadata", {})
    return meta.get("subject"), meta.get("major_or_minor")


def build_program_index(programs):
    index = {}
    duplicates = []

    for criteria in programs:
        key = program_key(criteria)
        if key in index:
            duplicates.append(key)
            continue
        index[key] = criteria

    return index, sorted(set(duplicates))


def parse_pathway(raw_text):
    tokens = re.split(r"[,;\n\t ]+", (raw_text or "").upper())
    parsed = [token.strip() for token in tokens if token.strip()]
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(parsed))


def course_first_sem(course):
    semesters = course.get("semesters") or []
    return min(semesters) if semesters else None


def course_year(course):
    sem = course_first_sem(course)
    if sem is None:
        return None
    return ((sem - 1) // 2) + 1


def index_courses(courses):
    return {
        c.get("course_code"): c
        for c in courses
        if c.get("course_code")
    }


def requirement_codes_by_set(criteria):
    set_rules = criteria.get("requirements_by_set", {})
    return {
        "set_a": list((set_rules.get("set_a") or {}).get("available_courses", [])),
        "set_b": list((set_rules.get("set_b") or {}).get("available_courses", [])),
        "set_c": list((set_rules.get("set_c") or {}).get("available_courses", [])),
        "set_d": list((set_rules.get("set_d") or {}).get("compulsory_courses", [])),
        "set_e": list((set_rules.get("set_e") or {}).get("not_counted_courses", [])),
    }


def collect_requirement_codes(criteria, selected_sets=None):
    by_set = requirement_codes_by_set(criteria)
    picked_sets = selected_sets or ["set_a", "set_b", "set_c", "set_d", "set_e"]
    out = set()
    for set_name in picked_sets:
        out.update(by_set.get(set_name, []))
    return out


def collect_code_to_sets(criteria):
    mapping = {}
    by_set = requirement_codes_by_set(criteria)

    for set_name, codes in by_set.items():
        for code in codes:
            mapping.setdefault(code, set()).add(set_name)

    return mapping


def filter_courses(courses, selected_subjects, selected_kinds, sem_range, query):
    filtered = []
    sem_min, sem_max = sem_range
    query_lower = (query or "").strip().lower()

    for course in courses:
        subject = course.get("subject")
        kind = course.get("kind")
        code = (course.get("course_code") or "").lower()
        name = (course.get("course_name") or "").lower()
        first_sem = course_first_sem(course)

        if subject not in selected_subjects:
            continue
        if kind not in selected_kinds:
            continue
        if first_sem is None or not (sem_min <= first_sem <= sem_max):
            continue
        if query_lower and query_lower not in code and query_lower not in name:
            continue

        filtered.append(course)

    return filtered


def expand_with_prereqs(filtered_courses, course_index):
    selected_codes = {
        c.get("course_code")
        for c in filtered_courses
        if c.get("course_code")
    }
    stack = list(selected_codes)

    while stack:
        code = stack.pop()
        course = course_index.get(code)
        if not course:
            continue

        for prereq in course.get("prerequisites", []):
            if prereq in course_index and prereq not in selected_codes:
                selected_codes.add(prereq)
                stack.append(prereq)

    expanded = [course_index[code] for code in selected_codes if code in course_index]
    expanded.sort(key=lambda c: (course_first_sem(c) or 999, c.get("course_code") or ""))
    return expanded


def remove_isolated_courses(courses):
    available_codes = {c.get("course_code") for c in courses if c.get("course_code")}
    connected = set()

    for course in courses:
        target = course.get("course_code")
        if not target:
            continue
        for prereq in course.get("prerequisites", []):
            if prereq in available_codes:
                connected.add(prereq)
                connected.add(target)

    if not connected:
        return []

    return [c for c in courses if c.get("course_code") in connected]


def _available_codes(courses):
    return {c.get("course_code") for c in courses if c.get("course_code")}


def make_semester_graph_elements(courses):
    nodes = []
    edges = []

    all_sems = sorted({course_first_sem(c) for c in courses if course_first_sem(c) is not None})

    for sem in all_sems:
        nodes.append(
            Node(
                id=f"group_sem_{sem}",
                properties={
                    "label": f"Semester {sem}",
                    "isGroup": True,
                },
            )
        )

    available_codes = _available_codes(courses)

    for course in courses:
        code = course.get("course_code")
        first_sem = course_first_sem(course)
        if not code or first_sem is None:
            continue

        color = COURSE_KIND_COLOR_MAP.get(course.get("kind"), "#6c757d")
        nodes.append(
            Node(
                id=code,
                properties={
                    "label": f"{code}\n{course.get('course_name', '')}",
                    "parent_id": f"group_sem_{first_sem}",
                    "color": color,
                    "credits": course.get("credits"),
                    "subject": course.get("subject"),
                    "kind": course.get("kind"),
                },
            )
        )

    for course in courses:
        target = course.get("course_code")
        if not target:
            continue

        for prereq in course.get("prerequisites", []):
            if prereq in available_codes:
                edges.append(Edge(id=f"{prereq}-{target}", start=prereq, end=target))

    return nodes, edges


def _pick_course_set(code_sets):
    priority = ["set_d", "set_a", "set_b", "set_c", "set_e"]
    for set_name in priority:
        if set_name in code_sets:
            return set_name
    return "support"


def make_program_roadmap_elements(
    criteria,
    course_index,
    include_prereq_support=True,
    selected_sets=None,
    year_range=(1, 4),
):
    selected_sets = selected_sets or ["set_a", "set_b", "set_c", "set_d", "set_e"]

    code_to_sets = collect_code_to_sets(criteria)
    base_codes = collect_requirement_codes(criteria, selected_sets)

    present_base_codes = {code for code in base_codes if code in course_index}
    selected_codes = set(present_base_codes)

    if include_prereq_support:
        stack = list(present_base_codes)
        while stack:
            code = stack.pop()
            course = course_index.get(code)
            if not course:
                continue

            for prereq in course.get("prerequisites", []):
                if prereq in course_index and prereq not in selected_codes:
                    selected_codes.add(prereq)
                    stack.append(prereq)

    y_min, y_max = year_range
    year_groups = [year for year in range(y_min, y_max + 1)]

    nodes = []
    edges = []

    for year in year_groups:
        nodes.append(
            Node(
                id=f"group_year_{year}",
                properties={"label": f"Year {year}", "isGroup": True},
            )
        )

    filtered_codes = set()
    for code in selected_codes:
        course = course_index.get(code)
        if not course:
            continue

        year = course_year(course)
        if year is None or not (y_min <= year <= y_max):
            continue

        filtered_codes.add(code)

        code_sets = code_to_sets.get(code, set())
        primary_set = _pick_course_set(code_sets)
        set_badge = primary_set.upper() if primary_set != "support" else "PREREQ"
        color = SET_COLOR_MAP.get(primary_set, SET_COLOR_MAP["support"])

        semester_text = ",".join(map(str, course.get("semesters", [])))
        label = f"{code}\n{course.get('course_name', '')}\nY{year} S[{semester_text}] {course.get('credits', 0)}cr {set_badge}"

        nodes.append(
            Node(
                id=code,
                properties={
                    "label": label,
                    "parent_id": f"group_year_{year}",
                    "color": color,
                    "subject": course.get("subject"),
                    "kind": course.get("kind"),
                    "role": primary_set,
                },
            )
        )

    for code in filtered_codes:
        course = course_index.get(code)
        if not course:
            continue

        for prereq in course.get("prerequisites", []):
            if prereq in filtered_codes:
                edges.append(Edge(id=f"{prereq}-{code}", start=prereq, end=code))

    return {
        "nodes": nodes,
        "edges": edges,
        "visible_codes": sorted(filtered_codes),
        "base_codes_present": sorted(present_base_codes),
        "base_codes_missing": sorted(base_codes.difference(present_base_codes)),
    }


def build_quality_report(courses, programs):
    all_codes = [c.get("course_code") for c in courses if c.get("course_code")]
    all_codes_set = set(all_codes)

    duplicate_course_codes = {
        code: count
        for code, count in Counter(all_codes).items()
        if count > 1
    }

    missing_prereq_links = {}
    self_prereq_courses = []
    missing_semesters = []

    for course in courses:
        code = course.get("course_code")
        if not code:
            continue

        semesters = course.get("semesters") or []
        if not semesters:
            missing_semesters.append(code)

        prereqs = course.get("prerequisites", [])
        if code in prereqs:
            self_prereq_courses.append(code)

        unknown_prereqs = [p for p in prereqs if p not in all_codes_set]
        if unknown_prereqs:
            missing_prereq_links[code] = unknown_prereqs

    program_counts = Counter(program_key(criteria) for criteria in programs)
    duplicate_program_entries = {
        f"{subject}::{program_type}": count
        for (subject, program_type), count in program_counts.items()
        if count > 1
    }

    unknown_requirement_codes = {}
    for criteria in programs:
        subject, program_type = program_key(criteria)
        pkey = f"{subject}::{program_type}"

        unknown_by_set = {}
        codes_by_set = requirement_codes_by_set(criteria)
        for set_name, codes in codes_by_set.items():
            unknown = sorted([code for code in codes if code not in all_codes_set])
            if unknown:
                unknown_by_set[set_name] = unknown

        if unknown_by_set:
            unknown_requirement_codes[pkey] = unknown_by_set

    return {
        "duplicate_course_codes": duplicate_course_codes,
        "missing_prereq_links": missing_prereq_links,
        "duplicate_program_entries": duplicate_program_entries,
        "unknown_requirement_codes": unknown_requirement_codes,
        "missing_semesters": sorted(missing_semesters),
        "self_prereq_courses": sorted(self_prereq_courses),
    }


def build_course_stats(courses, programs):
    subjects = {c.get("subject") for c in courses if c.get("subject")}
    kinds = Counter(c.get("kind") for c in courses if c.get("kind"))

    all_codes = _available_codes(courses)
    prereq_edges = 0
    for course in courses:
        for prereq in course.get("prerequisites", []):
            if prereq in all_codes:
                prereq_edges += 1

    credits = [c.get("credits", 0) for c in courses]

    return {
        "courses": len(courses),
        "programs": len(programs),
        "subjects": len(subjects),
        "prereq_edges": prereq_edges,
        "avg_credits": round(sum(credits) / len(credits), 2) if credits else 0,
        "kind_breakdown": dict(sorted(kinds.items())),
    }


def suggest_pathway(criteria, limit=18):
    code_sets = requirement_codes_by_set(criteria)
    ordered = []

    for set_name in ["set_d", "set_a", "set_c", "set_b", "set_e"]:
        for code in code_sets.get(set_name, []):
            if code not in ordered:
                ordered.append(code)

    return ", ".join(ordered[:limit])


if __name__ == "__main__":
    # Backward compatibility for older command habits:
    # streamlit run src/graph.py
    from app import main

    main()
