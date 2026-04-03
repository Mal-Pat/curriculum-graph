import json
import re
from collections import Counter
from pathlib import Path
import networkx as nx

from yfiles_graphs_for_streamlit import Edge, Node


DATA_DIR = Path("data")
DEFAULT_COURSES_PATH = Path("IISER-P/all_courses.json")
DEFAULT_MAJOR_MINOR_PATH = Path("IISER-P/major_minor_requirements.json")
DEFAULT_CONSTRAINTS_PATH = Path("IISER-P/college_constraints.json")

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


def load_constraints(constraints_relative: Path | None = None):
    relative = constraints_relative or DEFAULT_CONSTRAINTS_PATH
    return load_json(DATA_DIR / relative)


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
                edges.append(
                    Edge(
                        id=f"{prereq}-{target}",
                        start=prereq,
                        end=target,
                        properties={"directed": True, "edge_type": "prerequisite"},
                    )
                )

    return nodes, edges


def _normalized_semesters(semesters):
    out = set()
    for sem in semesters or []:
        try:
            out.add(int(sem))
        except (TypeError, ValueError):
            continue
    return sorted(out)


def _offering_pattern_label(semesters):
    sems = _normalized_semesters(semesters)
    if not sems:
        return "unknown"
    if sems == [5, 7]:
        return "offered in 5 and 7"
    if sems == [6, 8]:
        return "offered in 6 and 8"
    if all((sem % 2 == 1) for sem in sems):
        return "odd-sem offering"
    if all((sem % 2 == 0) for sem in sems):
        return "even-sem offering"
    return "mixed-sem offering"


def make_year_semester_graph_elements(courses):
    """Build graph clustered by year group with semester subgroups.

    Structure: Year group -> Semester subgroup -> Course nodes.
    Prerequisite edges remain course -> course across all visible courses.
    """

    nodes = []
    edges = []

    year_to_semesters = {}
    for course in courses:
        first_sem = course_first_sem(course)
        if first_sem is None:
            continue
        year = ((first_sem - 1) // 2) + 1
        year_to_semesters.setdefault(year, set()).add(first_sem)

    for year in sorted(year_to_semesters):
        year_group_id = f"group_catalog_year_{year}"
        nodes.append(
            Node(
                id=year_group_id,
                properties={
                    "label": f"Year {year}",
                    "isGroup": True,
                },
            )
        )

        for sem in sorted(year_to_semesters[year]):
            sem_parity = "Odd" if (sem % 2 == 1) else "Even"
            nodes.append(
                Node(
                    id=f"group_catalog_year_{year}_sem_{sem}",
                    properties={
                        "label": f"Semester {sem} ({sem_parity})",
                        "isGroup": True,
                        "parent_id": year_group_id,
                    },
                )
            )

    available_codes = _available_codes(courses)

    for course in courses:
        code = course.get("course_code")
        first_sem = course_first_sem(course)
        if not code or first_sem is None:
            continue

        year = ((first_sem - 1) // 2) + 1
        semesters = _normalized_semesters(course.get("semesters", []))
        sem_text = ",".join(map(str, semesters)) if semesters else "-"
        offering_pattern = _offering_pattern_label(semesters)

        color = COURSE_KIND_COLOR_MAP.get(course.get("kind"), "#6c757d")
        label = (
            f"{code}\\n{course.get('course_name', '')}"
            f"\\nY{year} S{first_sem} | {course.get('credits', 0)}cr"
            f"\\nOffered: {sem_text} ({offering_pattern})"
        )

        nodes.append(
            Node(
                id=code,
                properties={
                    "label": label,
                    "parent_id": f"group_catalog_year_{year}_sem_{first_sem}",
                    "color": color,
                    "credits": course.get("credits"),
                    "subject": course.get("subject"),
                    "kind": course.get("kind"),
                    "offering_pattern": offering_pattern,
                },
            )
        )

    for course in courses:
        target = course.get("course_code")
        if not target:
            continue

        for prereq in course.get("prerequisites", []):
            if prereq in available_codes:
                edges.append(
                    Edge(
                        id=f"catalog-{prereq}-{target}",
                        start=prereq,
                        end=target,
                        properties={"directed": True, "edge_type": "prerequisite"},
                    )
                )

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
    selection = collect_program_codes(
        criteria=criteria,
        course_index=course_index,
        selected_sets=selected_sets,
        include_prereq_support=include_prereq_support,
        year_range=year_range,
    )
    code_to_sets = selection["code_to_sets"]
    selected_codes = set(selection["visible_codes"])

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
                edges.append(
                    Edge(
                        id=f"{prereq}-{code}",
                        start=prereq,
                        end=code,
                        properties={"directed": True, "edge_type": "prerequisite"},
                    )
                )

    return {
        "nodes": nodes,
        "edges": edges,
        "visible_codes": sorted(filtered_codes),
        "base_codes_present": sorted(selection["base_codes_present"]),
        "base_codes_missing": sorted(selection["base_codes_missing"]),
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


def collect_program_codes(
    criteria,
    course_index,
    selected_sets=None,
    include_prereq_support=True,
    year_range=(1, 4),
):
    """Collect course codes for a selected program with optional prereq expansion.

    Returns a payload used by roadmap, analytics, and planning functions.
    """

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
    visible_codes = set()
    for code in selected_codes:
        course = course_index.get(code)
        if not course:
            continue

        year = course_year(course)
        if year is None:
            continue
        if y_min <= year <= y_max:
            visible_codes.add(code)

    return {
        "code_to_sets": code_to_sets,
        "visible_codes": visible_codes,
        "base_codes_present": present_base_codes,
        "base_codes_missing": base_codes.difference(present_base_codes),
    }


def build_dependency_digraph(course_index, selected_codes):
    """Build directed prerequisite graph: prereq -> dependent course."""

    graph = nx.DiGraph()

    for code in sorted(selected_codes):
        course = course_index.get(code)
        if not course:
            continue

        graph.add_node(
            code,
            course_name=course.get("course_name"),
            subject=course.get("subject"),
            credits=course.get("credits"),
            semesters=course.get("semesters", []),
            kind=course.get("kind"),
            first_sem=course_first_sem(course),
            year=course_year(course),
        )

    for code in sorted(selected_codes):
        course = course_index.get(code)
        if not course:
            continue

        for prereq in course.get("prerequisites", []):
            if prereq in selected_codes:
                graph.add_edge(prereq, code)

    return graph


def detect_cycles(graph):
    """Return list of directed cycles, each as ordered course-code list."""

    return [cycle for cycle in nx.simple_cycles(graph)]


def topological_order(graph):
    """Return topological ordering if DAG, else empty list."""

    if not nx.is_directed_acyclic_graph(graph):
        return []
    return list(nx.topological_sort(graph))


def unreachable_from_start(graph, course_index, start_semester=1):
    """Find nodes unreachable from feasible start nodes at chosen semester."""

    starters = []
    for code in graph.nodes:
        course = course_index.get(code, {})
        semesters = course.get("semesters") or []
        if not semesters:
            continue
        # Root nodes are feasible if at least one offering exists at/after start.
        if graph.in_degree(code) == 0 and max(semesters) >= start_semester:
            starters.append(code)

    reachable = set(starters)
    for source in starters:
        reachable.update(nx.descendants(graph, source))

    return {
        "starters": sorted(starters),
        "reachable": sorted(reachable),
        "unreachable": sorted(set(graph.nodes).difference(reachable)),
    }


def representative_paths(
    graph,
    target_codes,
    max_paths_per_target=3,
    max_depth=12,
):
    """Collect representative source->target prerequisite paths.

    Exhaustive path enumeration can be expensive; this returns up to
    `max_paths_per_target` per target.
    """

    roots = [node for node, indeg in graph.in_degree() if indeg == 0]
    out = {}

    for target in target_codes:
        if target not in graph:
            continue

        found = []
        for root in roots:
            if len(found) >= max_paths_per_target:
                break

            if root == target:
                found.append([target])
                continue

            if not nx.has_path(graph, root, target):
                continue

            for path in nx.all_simple_paths(graph, root, target, cutoff=max_depth):
                found.append(path)
                if len(found) >= max_paths_per_target:
                    break

        if not found:
            found = [[target]]

        out[target] = found

    return out


def bottleneck_table(graph, top_n=12):
    """Compute bottleneck indicators for courses in directed graph."""

    if graph.number_of_nodes() == 0:
        return []

    betweenness = nx.betweenness_centrality(graph) if graph.number_of_nodes() > 1 else {}
    rows = []

    for code in graph.nodes:
        rows.append(
            {
                "course_code": code,
                "in_degree": graph.in_degree(code),
                "direct_dependents": graph.out_degree(code),
                "all_downstream": len(nx.descendants(graph, code)),
                "betweenness": round(float(betweenness.get(code, 0.0)), 4),
            }
        )

    rows.sort(
        key=lambda row: (
            row["all_downstream"],
            row["direct_dependents"],
            row["betweenness"],
        ),
        reverse=True,
    )
    return rows[:top_n]


def plan_courses_by_term(
    graph,
    course_index,
    start_semester=1,
    max_courses_per_term=4,
    max_terms=8,
    priority_codes=None,
    already_completed=None,
    max_credits_per_term=None,
):
    """Build a constrained term-by-term plan for selected graph nodes."""

    if not nx.is_directed_acyclic_graph(graph):
        return {
            "is_complete": False,
            "reason": "Graph has prerequisite cycles",
            "plan": {},
            "scheduled": [],
            "blocked": sorted(graph.nodes),
            "blocked_details": [],
        }

    priority_codes = set(priority_codes or [])
    completed = set(already_completed or []).intersection(set(graph.nodes))
    remaining = set(graph.nodes).difference(completed)
    plan = {}

    start = int(start_semester)
    end = start + int(max_terms) - 1

    for semester in range(start, end + 1):
        available = []
        for code in sorted(remaining):
            course = course_index.get(code, {})
            offered = semester in (course.get("semesters") or [])
            if not offered:
                continue

            prereqs = set(graph.predecessors(code))
            if prereqs.issubset(completed):
                available.append(code)

        available.sort(
            key=lambda code: (
                0 if code in priority_codes else 1,
                -graph.out_degree(code),
                code,
            )
        )

        chosen = []
        credit_cap = int(max_credits_per_term) if max_credits_per_term is not None else None
        chosen_credits = 0

        for code in available:
            if len(chosen) >= int(max_courses_per_term):
                break

            course_credits = int(course_index.get(code, {}).get("credits", 0) or 0)
            if credit_cap is not None and chosen_credits + course_credits > credit_cap:
                continue

            chosen.append(code)
            chosen_credits += course_credits

        if chosen:
            plan[semester] = chosen
            completed.update(chosen)
            remaining.difference_update(chosen)

        if not remaining:
            break

    blocked = sorted(remaining)
    blocked_details = []
    for code in blocked:
        prereqs = sorted(set(graph.predecessors(code)).difference(completed))
        course = course_index.get(code, {})
        offered_terms = course.get("semesters") or []
        blocked_details.append(
            {
                "course_code": code,
                "unsatisfied_prereqs": prereqs,
                "offered_terms": offered_terms,
            }
        )

    return {
        "is_complete": len(blocked) == 0,
        "reason": "complete" if len(blocked) == 0 else "constraints_or_prereqs_blocked",
        "plan": plan,
        "scheduled": sorted(completed),
        "blocked": blocked,
        "blocked_details": blocked_details,
    }


def build_program_dependency_analysis(
    criteria,
    course_index,
    selected_sets=None,
    include_prereq_support=True,
    year_range=(1, 4),
    start_semester=1,
    max_courses_per_term=4,
    max_terms=8,
    already_completed=None,
    max_credits_per_term=None,
):
    """Full analysis payload for dependency graph + planning dashboard."""

    selection = collect_program_codes(
        criteria=criteria,
        course_index=course_index,
        selected_sets=selected_sets,
        include_prereq_support=include_prereq_support,
        year_range=year_range,
    )

    selected_codes = selection["visible_codes"]
    graph = build_dependency_digraph(course_index, selected_codes)

    cycles = detect_cycles(graph)
    topo = topological_order(graph)

    compulsory = set(requirement_codes_by_set(criteria).get("set_d", []))
    present_compulsory = sorted([code for code in compulsory if code in selected_codes])

    reachability = unreachable_from_start(
        graph=graph,
        course_index=course_index,
        start_semester=start_semester,
    )

    plan = plan_courses_by_term(
        graph=graph,
        course_index=course_index,
        start_semester=start_semester,
        max_courses_per_term=max_courses_per_term,
        max_terms=max_terms,
        priority_codes=present_compulsory,
        already_completed=already_completed,
        max_credits_per_term=max_credits_per_term,
    )

    rep_paths = representative_paths(
        graph=graph,
        target_codes=present_compulsory[:8],
        max_paths_per_target=3,
        max_depth=12,
    )

    return {
        "graph": graph,
        "cycles": cycles,
        "topological_order": topo,
        "bottlenecks": bottleneck_table(graph),
        "reachability": reachability,
        "representative_paths": rep_paths,
        "plan": plan,
        "selected_codes": sorted(selected_codes),
        "base_codes_present": sorted(selection["base_codes_present"]),
        "base_codes_missing": sorted(selection["base_codes_missing"]),
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "is_dag": len(cycles) == 0,
    }


if __name__ == "__main__":
    # Backward compatibility for older command habits:
    # streamlit run src/graph.py
    from app import main

    main()
