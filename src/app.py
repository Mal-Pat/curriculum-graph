import json
import sys
from pathlib import Path

import graph as cg
import streamlit as st
from validate_major_minor import validate_major_minor_pathway
from yfiles_graphs_for_streamlit import Layout, StreamlitGraphWidget


LAYOUT_OPTIONS = {
    "Hierarchic": Layout.HIERARCHIC,
    "Orthogonal": Layout.ORTHOGONAL,
    "Organic": Layout.ORGANIC,
    "Radial": Layout.RADIAL,
    "Tree": Layout.TREE,
}


def _layout_selector(label, key, default="Hierarchic"):
    names = list(LAYOUT_OPTIONS.keys())
    default_idx = names.index(default) if default in names else 0
    selected = st.selectbox(label, options=names, index=default_idx, key=key)
    return LAYOUT_OPTIONS[selected]


def _safe_show_graph(
    widget,
    graph_layout,
    key,
    directed=True,
    sync_selection=False,
    sidebar=None,
    neighborhood=None,
):
    sidebar_cfg = sidebar if sidebar is not None else {"enabled": False}
    neighborhood_cfg = neighborhood if neighborhood is not None else {"max_distance": 1, "selected_nodes": []}
    try:
        return widget.show(
            directed=directed,
            graph_layout=graph_layout,
            sync_selection=sync_selection,
            sidebar=sidebar_cfg,
            neighborhood=neighborhood_cfg,
            overview=True,
            key=key,
        )
    except Exception as err:
        st.error("Graph could not be rendered. Check filters or graph structure.")
        st.caption(f"Renderer error: {err}")
        return [], []


def _force_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def _show_df(data, **kwargs):
    """Render dataframes with forward-compatible width handling.

    Streamlit deprecated use_container_width in favor of width. This helper
    keeps old call sites readable while normalizing behavior in one place.
    """

    if "use_container_width" in kwargs and "width" not in kwargs:
        use_container = kwargs.pop("use_container_width")
        kwargs["width"] = "stretch" if use_container else "content"
    kwargs.setdefault("width", "stretch")
    st.dataframe(data, **kwargs)


def _inject_design():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Source+Sans+3:wght@400;600;700&display=swap');

        :root {
            --bg-a: #f2f7f8;
            --bg-b: #f9efe4;
            --ink: #102a43;
            --muted: #486581;
            --accent: #0f766e;
            --accent-2: #f59e0b;
            --card: rgba(255, 255, 255, 0.78);
            --line: #d9e2ec;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 18%, rgba(15, 118, 110, 0.14), transparent 40%),
                radial-gradient(circle at 88% 5%, rgba(245, 158, 11, 0.16), transparent 33%),
                linear-gradient(180deg, var(--bg-a) 0%, var(--bg-b) 100%);
        }

        html, body, [class*="css"] {
            font-family: 'Source Sans 3', sans-serif;
            color: var(--ink);
        }

        h1, h2, h3, h4 {
            font-family: 'Space Grotesk', sans-serif;
            letter-spacing: 0.2px;
        }

        .main .block-container {
            max-width: 1350px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }

        .hero {
            background: linear-gradient(125deg, #0f766e 0%, #155e75 52%, #f59e0b 100%);
            border-radius: 22px;
            padding: 1.2rem 1.3rem;
            color: #f8fafc;
            box-shadow: 0 14px 30px rgba(15, 118, 110, 0.28);
            margin-bottom: 1rem;
            animation: fade-up 360ms ease-out;
        }

        .hero h1 {
            margin: 0;
            font-size: 2rem;
            letter-spacing: 0.3px;
        }

        .hero p {
            margin: 0.35rem 0 0 0;
            opacity: 0.95;
            font-size: 1rem;
        }

        [data-testid="stMetric"] {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 0.45rem 0.65rem;
            backdrop-filter: blur(2px);
            box-shadow: 0 6px 14px rgba(16, 42, 67, 0.06);
            animation: fade-up 400ms ease-out;
        }

        .stButton > button {
            border-radius: 999px;
            border: 1px solid rgba(15, 118, 110, 0.4);
            box-shadow: 0 6px 14px rgba(15, 118, 110, 0.18);
            transition: transform 120ms ease, box-shadow 120ms ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 18px rgba(15, 118, 110, 0.24);
        }

        div[data-baseweb="select"] > div {
            border-radius: 12px;
            border-color: var(--line);
            background: rgba(255, 255, 255, 0.82);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 6px 14px rgba(16, 42, 67, 0.06);
        }

        [data-testid="stProgressBar"] > div > div {
            background: linear-gradient(90deg, #0f766e, #f59e0b);
        }

        [data-testid="stSlider"] [role="slider"] {
            background: #0f766e;
            border-color: #0f766e;
        }

        .kpi-band {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(249, 239, 228, 0.72));
            border: 1px solid rgba(15, 118, 110, 0.22);
            border-radius: 14px;
            padding: 0.6rem 0.8rem;
            margin-bottom: 0.8rem;
            color: #334e68;
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.65);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 12px;
            font-weight: 600;
            padding-left: 14px;
            padding-right: 14px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.72);
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #0f766e, #155e75);
            color: white;
            border-color: transparent;
        }

        .planner-note {
            background: rgba(15, 118, 110, 0.10);
            border: 1px solid rgba(15, 118, 110, 0.2);
            border-radius: 12px;
            padding: 0.55rem 0.75rem;
            color: #0f5132;
            margin: 0.2rem 0 0.8rem 0;
        }

        .soft-panel {
            background: rgba(255, 255, 255, 0.68);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 0.55rem 0.75rem;
            margin: 0.2rem 0 0.8rem 0;
            color: var(--muted);
        }

        .selection-panel {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.86), rgba(242, 247, 248, 0.9));
            border: 1px solid rgba(21, 94, 117, 0.2);
            border-radius: 14px;
            padding: 0.6rem 0.8rem;
            margin: 0.3rem 0 0.7rem 0;
            color: #1f2937;
        }

        .legend-wrap {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 0.45rem 0.65rem;
            margin: 0.35rem 0 0.65rem 0;
        }

        .legend-title {
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 0.35rem;
        }

        .legend-row {
            display: flex;
            gap: 0.45rem;
            flex-wrap: wrap;
        }

        .legend-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.32rem;
            border-radius: 999px;
            padding: 0.18rem 0.5rem;
            border: 1px solid #cbd5e1;
            background: #f8fafc;
            color: #334155;
            font-size: 0.82rem;
            font-weight: 600;
        }

        .legend-dot {
            width: 10px;
            height: 10px;
            border-radius: 999px;
            border: 1px solid rgba(15, 23, 42, 0.24);
        }

        .mode-chip {
            background: linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(21, 94, 117, 0.1));
            border: 1px solid rgba(15, 118, 110, 0.28);
            border-radius: 12px;
            padding: 0.5rem 0.7rem;
            margin: 0.25rem 0 0.85rem 0;
            color: #134e4a;
            font-weight: 600;
        }

        @keyframes fade-up {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 900px) {
            .main .block-container {
                padding-top: 0.8rem;
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }
            .hero h1 {
                font-size: 1.45rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _hero():
    st.markdown(
        """
        <div class="hero">
          <h1>Curriculum Graph Studio</h1>
          <p>Plan smarter across Semester 1-8: track credits to 184, compare major-minor pathways, and de-risk prerequisites early.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _is_student_mode():
    return bool(st.session_state.get("ui_student_mode", True))


def _render_color_legend(title, items):
    chips = "".join(
        [
            f"<span class='legend-chip'><span class='legend-dot' style='background:{color}'></span>{label}</span>"
            for label, color in items
        ]
    )
    st.markdown(
        (
            "<div class='legend-wrap'>"
            f"<div class='legend-title'>{title}</div>"
            f"<div class='legend-row'>{chips}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _major_minor_combined_elements(
    major_criteria,
    minor_criteria,
    course_index,
    include_prereq_support=True,
    year_range=(1, 4),
):
    major_selection = cg.collect_program_codes(
        criteria=major_criteria,
        course_index=course_index,
        include_prereq_support=include_prereq_support,
        year_range=year_range,
    )
    minor_selection = cg.collect_program_codes(
        criteria=minor_criteria,
        course_index=course_index,
        include_prereq_support=include_prereq_support,
        year_range=year_range,
    )

    major_base = cg.collect_requirement_codes(major_criteria)
    minor_base = cg.collect_requirement_codes(minor_criteria)

    combined_codes = set(major_selection["visible_codes"]).union(minor_selection["visible_codes"])
    graph = cg.build_dependency_digraph(course_index, combined_codes)

    y_min, y_max = year_range
    nodes = []
    edges = []
    role_lookup = {}

    for year in range(y_min, y_max + 1):
        nodes.append(
            cg.Node(
                id=f"group_combined_year_{year}",
                properties={
                    "label": f"Year {year}",
                    "isGroup": True,
                    "color": "#dbeafe",
                },
            )
        )

    for code in sorted(graph.nodes):
        course = course_index.get(code, {})
        year = cg.course_year(course)
        if year is None or not (y_min <= year <= y_max):
            continue

        in_major = code in major_base
        in_minor = code in minor_base
        if in_major and in_minor:
            role = "both"
        elif in_major:
            role = "major"
        elif in_minor:
            role = "minor"
        else:
            role = "support"

        label = f"{code}\n{course.get('course_name', '')}\n{role.upper()}"
        role_lookup[code] = role
        nodes.append(
            cg.Node(
                id=code,
                properties={
                    "label": label,
                    "parent_id": f"group_combined_year_{year}",
                    "color": ROLE_COLOR_MAP[role],
                    "role": role,
                },
            )
        )

    for start, end in graph.edges:
        edges.append(
            cg.Edge(
                id=f"combined-{start}-{end}",
                start=start,
                end=end,
                properties={"directed": True, "edge_type": "prerequisite"},
            )
        )

    return nodes, edges, graph, role_lookup


def _course_rows(codes, course_index):
    rows = []
    for code in sorted(set(codes)):
        course = course_index.get(code)
        if not course:
            rows.append(
                {
                    "Code": code,
                    "Exists": False,
                    "Name": "(missing in all_courses)",
                    "Subject": "-",
                    "Credits": "-",
                    "Semesters": "-",
                }
            )
            continue

        rows.append(
            {
                "Code": code,
                "Exists": True,
                "Name": course.get("course_name"),
                "Subject": course.get("subject"),
                "Credits": course.get("credits"),
                "Semesters": ", ".join(map(str, course.get("semesters", []))),
            }
        )
    return rows


def _semester_pair_rows(courses, pair):
    pset = set(pair)
    rows = []

    for course in sorted(courses, key=lambda c: c.get("course_code") or ""):
        semesters = set(course.get("semesters") or [])
        if not pset.issubset(semesters):
            continue

        rows.append(
            {
                "Code": course.get("course_code"),
                "Name": course.get("course_name"),
                "Subject": course.get("subject"),
                "Credits": course.get("credits"),
                "Semesters": ", ".join(map(str, sorted(semesters))),
            }
        )

    return rows


SET_ORDER = ["set_a", "set_b", "set_c", "set_d", "set_e"]

ALLOWED_MAJOR_KEYS = {
    "physics",
    "chemistry",
    "biology",
    "earthandclimatescience",
    "ecs",
}

ALLOWED_MINOR_KEYS = {
    "physics",
    "chemistry",
    "biology",
    "earthandclimatescience",
    "ecs",
    "datascience",
    "ds",
}

GRAPH_VISUAL_PROFILES = {
    "Readable": {"node_scale": 1.18, "group_scale": 1.35, "edge_scale": 1.45},
    "Balanced": {"node_scale": 1.0, "group_scale": 1.2, "edge_scale": 1.0},
    "Compact": {"node_scale": 0.88, "group_scale": 1.05, "edge_scale": 0.82},
}

ROLE_COLOR_MAP = {
    "major": "#1d4ed8",
    "minor": "#0f766e",
    "both": "#c2410c",
    "support": "#475569",
}


def _subject_key(subject):
    """Normalize subject labels to a comparison-friendly key."""

    return "".join(ch for ch in str(subject).lower() if ch.isalnum())


def _is_allowed_program(subject, program_type):
    """Return whether a program entry is allowed by IISER policy filters."""

    key = _subject_key(subject)
    p_type = (program_type or "").strip().lower()
    if p_type == "major":
        return key in ALLOWED_MAJOR_KEYS
    if p_type == "minor":
        return key in ALLOWED_MINOR_KEYS
    return False


def _filter_program_index_for_policy(program_index):
    """Filter program index to only allowed major/minor offerings."""

    filtered = {}
    removed = []
    for (subject, p_type), criteria in program_index.items():
        if _is_allowed_program(subject, p_type):
            filtered[(subject, p_type)] = criteria
        else:
            removed.append((subject, p_type))
    return filtered, sorted(removed)


def _foundation_compulsory_codes(constraints, upto_semester=3):
    rows = []
    for sem_block in (constraints or {}).get("semesters", []):
        sem_no = int(sem_block.get("semester_number", 0) or 0)
        if sem_no == 0 or sem_no > int(upto_semester):
            continue
        for code in sem_block.get("compulsory_courses") or []:
            rows.append(code)
    return list(dict.fromkeys(rows))


def _friendly_requirement_buckets(criteria):
    by_set = cg.requirement_codes_by_set(criteria)
    compulsory = set(by_set.get("set_d", []))
    excluded = set(by_set.get("set_e", []))
    electives = (
        set(by_set.get("set_a", []))
        .union(set(by_set.get("set_b", [])))
        .union(set(by_set.get("set_c", [])))
        .difference(compulsory)
        .difference(excluded)
    )
    return {
        "compulsory": sorted(compulsory),
        "electives": sorted(electives),
        "excluded": sorted(excluded),
    }


def _code_requirement_label_lookup(criteria):
    buckets = _friendly_requirement_buckets(criteria)
    out = {}
    for code in buckets["compulsory"]:
        out[code] = "Compulsory"
    for code in buckets["electives"]:
        out[code] = "Elective option"
    for code in buckets["excluded"]:
        out[code] = "Not counted"
    return out


def _set_rule_description(set_name, rule):
    if set_name == "set_a":
        min_req = int((rule or {}).get("minimum_required_from_set", 0) or 0)
        return f"Take at least {min_req}"
    if set_name == "set_b":
        max_allowed = (rule or {}).get("maximum_allowed_from_set")
        return f"Take at most {max_allowed}" if max_allowed is not None else "No cap"
    if set_name == "set_d":
        required_count = len((rule or {}).get("compulsory_courses", []) or [])
        return f"Take all compulsory ({required_count})"
    if set_name == "set_e":
        return "Excluded from counting"
    return "Supplementary/choice pool"


def _set_rule_rows(criteria):
    rules = (criteria or {}).get("requirements_by_set", {}) or {}
    by_set = cg.requirement_codes_by_set(criteria)
    rows = []
    for set_name in SET_ORDER:
        rule = rules.get(set_name) or {}
        rows.append(
            {
                "Set": set_name.upper(),
                "Configured": bool(rule),
                "Listed courses": len(by_set.get(set_name, [])),
                "Rule": _set_rule_description(set_name, rule),
            }
        )
    return rows


def _set_progress_rows(validation_result):
    breakdown = (validation_result or {}).get("set_breakdown", {}) or {}
    rows = []

    for set_name in SET_ORDER:
        data = breakdown.get(set_name, {})
        if not data:
            rows.append(
                {
                    "Set": set_name.upper(),
                    "Satisfied": "-",
                    "Taken": 0,
                    "Rule check": "No details",
                }
            )
            continue

        if set_name == "set_a":
            rule_text = f"min {data.get('required_min', 0)} | remaining {data.get('remaining_to_min', 0)}"
        elif set_name == "set_b":
            rule_text = (
                f"max {data.get('allowed_max')} | over by {data.get('over_by', 0)}"
                if data.get("allowed_max") is not None
                else "no max cap"
            )
        elif set_name == "set_d":
            rule_text = f"required {data.get('required_count', 0)} | missing {len(data.get('missing_required', []))}"
        elif set_name == "set_e":
            rule_text = f"excluded {data.get('excluded_count', 0)}"
        else:
            rule_text = "informational"

        rows.append(
            {
                "Set": set_name.upper(),
                "Satisfied": "Yes" if data.get("is_satisfied") else "No",
                "Taken": data.get("taken_count", data.get("excluded_count", 0)),
                "Rule check": rule_text,
            }
        )

    return rows


def _not_selected_requirement_rows(criteria, selected_codes, course_index, program_label):
    selected = set(selected_codes or [])
    code_to_label = _code_requirement_label_lookup(criteria)
    rows = []

    for code in sorted(code_to_label):
        if code in selected:
            continue

        course = course_index.get(code, {})
        rows.append(
            {
                "Program": program_label,
                "Code": code,
                "Category": code_to_label.get(code, "-"),
                "Name": course.get("course_name", "(missing in all_courses)"),
                "Credits": course.get("credits", "-"),
            }
        )

    return rows


def _selected_graph_course_codes(selected_nodes, group_prefixes):
    prefixes = tuple(group_prefixes)
    picked = []
    for node in selected_nodes or []:
        node_id = node.get("id") if hasattr(node, "get") else None
        if not node_id or any(node_id.startswith(prefix) for prefix in prefixes):
            continue
        picked.append(node_id)
    return list(dict.fromkeys(sorted(picked)))


def _selected_course_detail_rows(selected_codes, course_index, set_lookup=None, role_lookup=None):
    dependents = {}
    for code, course in course_index.items():
        for prereq in course.get("prerequisites", []):
            dependents.setdefault(prereq, []).append(code)

    rows = []
    for code in sorted(
        selected_codes,
        key=lambda x: (
            cg.course_first_sem(course_index.get(x, {})) or 999,
            x,
        ),
    ):
        course = course_index.get(code, {})
        requirement_text = "-"
        if set_lookup and code in set_lookup:
            raw_value = set_lookup.get(code)
            if isinstance(raw_value, str):
                requirement_text = raw_value
            elif isinstance(raw_value, (set, list, tuple)):
                names = []
                for value in raw_value:
                    if value == "set_d":
                        names.append("Compulsory")
                    elif value in ["set_a", "set_b", "set_c"]:
                        names.append("Elective option")
                    elif value == "set_e":
                        names.append("Not counted")
                    else:
                        names.append(str(value))
                requirement_text = ", ".join(sorted(set(names)))

        role_text = (role_lookup or {}).get(code, "-")
        prereq_text = ", ".join(sorted(course.get("prerequisites", []))) or "-"
        unlocks_text = ", ".join(sorted(dependents.get(code, []))) or "-"
        first_sem = cg.course_first_sem(course)
        year = cg.course_year(course)

        rows.append(
            {
                "Code": code,
                "Name": course.get("course_name", "(missing in all_courses)"),
                "Role": str(role_text).upper() if role_text != "-" else "-",
                "Requirement": requirement_text,
                "Credits": course.get("credits", "-"),
                "Year": year if year is not None else "-",
                "First Sem": first_sem if first_sem is not None else "-",
                "Semesters": ", ".join(map(str, course.get("semesters", []))) or "-",
                "Prerequisites": prereq_text,
                "Unlocks": unlocks_text,
            }
        )

    return rows


def _year_semester_distribution_rows(course_codes, course_index):
    buckets = {}

    for code in sorted(set(course_codes or [])):
        course = course_index.get(code)
        if not course:
            continue

        first_sem = cg.course_first_sem(course)
        if first_sem is None:
            continue

        year = cg.course_year(course)
        key = (year, first_sem)
        bucket = buckets.setdefault(
            key,
            {
                "Year": year,
                "Semester": first_sem,
                "Courses": 0,
                "Credits": 0,
                "Course Codes": [],
            },
        )

        bucket["Courses"] += 1
        bucket["Credits"] += int(course.get("credits", 0) or 0)
        bucket["Course Codes"].append(code)

    rows = []
    for _, row in sorted(buckets.items(), key=lambda item: item[0][1]):
        codes = row["Course Codes"]
        row["Course Codes"] = ", ".join(codes[:10]) + (" ..." if len(codes) > 10 else "")
        rows.append(row)

    return rows


def _render_year_semester_distribution(title, course_codes, course_index):
    rows = _year_semester_distribution_rows(course_codes, course_index)
    if not rows:
        st.info("No year-semester distribution available for this selection.")
        return

    total_courses = sum(row["Courses"] for row in rows)
    total_credits = sum(row["Credits"] for row in rows)
    covered_years = len(set(row["Year"] for row in rows))
    covered_semesters = len(rows)

    st.markdown(f"#### {title}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Years covered", covered_years)
    c2.metric("Semesters covered", covered_semesters)
    c3.metric("Courses in view", total_courses)
    c4.metric("Credits in view", total_credits)
    _show_df(rows, use_container_width=True)


def _edge_endpoints(edge):
    """Read edge endpoints from either dict-like or object-style edge payloads."""

    if isinstance(edge, dict):
        return edge.get("start"), edge.get("end")

    start = getattr(edge, "start", None)
    end = getattr(edge, "end", None)

    if start is None and hasattr(edge, "get"):
        start = edge.get("start")
    if end is None and hasattr(edge, "get"):
        end = edge.get("end")

    return start, end


def _semester_transition_rows(edges, course_index):
    """Build transition counts from prerequisite edges grouped by semester."""

    transition_counts = {}

    for edge in edges:
        start, end = _edge_endpoints(edge)
        if not start or not end:
            continue

        start_sem = cg.course_first_sem(course_index.get(start, {}))
        end_sem = cg.course_first_sem(course_index.get(end, {}))
        if start_sem is None or end_sem is None:
            continue

        key = (start_sem, end_sem)
        transition_counts[key] = transition_counts.get(key, 0) + 1

    rows = []
    for (from_sem, to_sem), count in sorted(transition_counts.items()):
        rows.append(
            {
                "From semester": from_sem,
                "To semester": to_sem,
                "Transition": f"S{from_sem} -> S{to_sem}",
                "Prereq links": count,
            }
        )

    return rows


def _render_semester_transition_summary(edges, course_index):
    """Show semester-to-semester transition table for the current graph."""

    rows = _semester_transition_rows(edges, course_index)
    if not rows:
        st.info("No semester transition summary available for current graph.")
        return

    st.markdown("#### Semester-to-Semester Prerequisite Transitions")
    _show_df(rows, use_container_width=True)


def _render_graph_support_tables(distribution_title, course_codes, edges, course_index, expanded=False):
    with st.expander("Graph insights tables", expanded=expanded):
        _render_year_semester_distribution(distribution_title, course_codes, course_index)
        _render_semester_transition_summary(edges, course_index)


def _graph_clarity_controls(prefix, default_layout="Hierarchic", student_mode=False):
    with st.expander("Graph Clarity Controls", expanded=False):
        if student_mode:
            use_student_defaults = st.checkbox(
                "Use student-friendly graph defaults",
                value=True,
                key=f"{prefix}_student_defaults",
                help="Readable labels and simpler prerequisite arrows for easier scanning.",
            )
            if use_student_defaults:
                st.caption(
                    "Preset active: Readable nodes, Code + Name labels, within-year prerequisite arrows."
                )
                return {
                    "visual_mode": "Readable",
                    "label_mode": "Code + Name",
                    "edge_mode": "Within same year",
                    "layout": LAYOUT_OPTIONS.get(default_layout, Layout.HIERARCHIC),
                }

        c1, c2, c3, c4 = st.columns(4)
        visual_mode = c1.selectbox(
            "Visual mode",
            options=["Readable", "Balanced", "Compact"],
            index=0,
            key=f"{prefix}_visual_mode",
        )
        label_mode = c2.selectbox(
            "Label mode",
            options=["Code only", "Code + Name", "Detailed"],
            index=1,
            key=f"{prefix}_label_mode",
        )
        edge_mode = c3.selectbox(
            "Prerequisite arrows",
            options=["All", "Within same year", "Hide arrows"],
            index=0,
            key=f"{prefix}_edge_mode",
        )
        layout = _layout_selector("Graph layout", key=f"{prefix}_layout", default=default_layout)

    return {
        "visual_mode": visual_mode,
        "label_mode": label_mode,
        "edge_mode": edge_mode,
        "layout": layout,
    }


def _filtered_edges_for_mode(edges, course_index, edge_mode):
    if edge_mode == "Hide arrows":
        return []
    if edge_mode != "Within same year":
        return list(edges)

    out = []
    for edge in edges:
        start, end = _edge_endpoints(edge)
        if not start or not end:
            continue

        start_year = cg.course_year(course_index.get(start, {}))
        end_year = cg.course_year(course_index.get(end, {}))
        if start_year is None or end_year is None:
            out.append(edge)
        elif start_year == end_year:
            out.append(edge)

    return out


def _apply_graph_visual_profile(nodes, edges, course_index, visual_mode, label_mode):
    profile = GRAPH_VISUAL_PROFILES.get(visual_mode, GRAPH_VISUAL_PROFILES["Balanced"])

    for node in nodes:
        node_id = node.get("id") if hasattr(node, "get") else None
        if not node_id:
            continue

        if str(node_id).startswith("group_"):
            node["visual_scale"] = profile["group_scale"]
            continue

        node["visual_scale"] = profile["node_scale"]
        course = course_index.get(node_id, {})
        if label_mode == "Code only":
            node["label"] = node_id
        elif label_mode == "Code + Name":
            node["label"] = f"{node_id}\n{course.get('course_name', '')}"

    for edge in edges:
        edge["edge_scale"] = profile["edge_scale"]

    return nodes, edges


def _subject_type_selector(program_index, key_prefix):
    subjects = sorted({subject for (subject, _) in program_index})
    if not subjects:
        return None, None

    subject = st.selectbox("Subject", subjects, key=f"{key_prefix}_subject")
    types = sorted({p_type for (subj, p_type) in program_index if subj == subject})
    p_type = st.radio("Program type", options=types, horizontal=True, key=f"{key_prefix}_type")
    return subject, p_type


def _render_overview(courses, programs):
    stats = cg.build_course_stats(courses, programs)

    st.markdown(
        """
        <div class="kpi-band">
            Deployment view: concise KPIs first, then interactive graph exploration with year-semester clarity.
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Courses", stats["courses"])
    c2.metric("Programs", stats["programs"])
    c3.metric("Subjects", stats["subjects"])
    c4.metric("Prereq Edges", stats["prereq_edges"])
    c5.metric("Avg Credits", stats["avg_credits"])

    st.caption(
        "Kind distribution: "
        + ", ".join([f"{k}={v}" for k, v in stats["kind_breakdown"].items()])
    )


def _render_catalog_graph(courses, course_index, program_index, constraints):
    st.subheader("Student Course Map")
    st.caption("Year boxes contain semester clusters; arrows show prerequisite flow across the map.")
    student_mode = _is_student_mode()

    if student_mode:
        st.markdown(
            """
            <div class="mode-chip">
                Student mode active: simplified graph defaults and cleaner summaries.
            </div>
            """,
            unsafe_allow_html=True,
        )

    focus_codes = None

    foundation_codes = [code for code in _foundation_compulsory_codes(constraints, upto_semester=3) if code in course_index]
    sem3_group_options = []
    sem3_group_cap = None
    for sem_block in (constraints or {}).get("semesters", []):
        sem_no = int(sem_block.get("semester_number", 0) or 0)
        if sem_no != 3:
            continue
        max_group = sem_block.get("max_group") or {}
        sem3_group_cap = max_group.get("max_allowed")
        sem3_group_options = list(max_group.get("available_courses") or [])

    with st.expander("Common Compulsory Structure (Sem 1-3)", expanded=False):
        _show_df(_course_rows(foundation_codes, course_index), use_container_width=True)
        if sem3_group_options:
            st.caption(
                f"Semester 3 common elective options (pick up to {sem3_group_cap}): "
                + ", ".join(sem3_group_options)
            )

    with st.expander("Filter panel", expanded=True):
        subject_options = sorted({c.get("subject") for c in courses if c.get("subject")})
        kind_options = sorted({c.get("kind") for c in courses if c.get("kind")})

        sem_values = [cg.course_first_sem(c) for c in courses if cg.course_first_sem(c) is not None]
        sem_min = min(sem_values)
        sem_max = max(sem_values)

        left, right = st.columns(2)
        selected_subjects = set(left.multiselect("Subjects", subject_options, default=subject_options))
        selected_kinds = set(right.multiselect("Kinds", kind_options, default=kind_options))

        sem_range = st.slider(
            "First-offered semester range",
            min_value=sem_min,
            max_value=sem_max,
            value=(sem_min, sem_max),
        )
        year_options = sorted({cg.course_year(c) for c in courses if cg.course_year(c) is not None})
        selected_years = st.multiselect(
            "Focus years",
            options=year_options,
            default=year_options,
        )
        offered_sem_options = sorted({int(sem) for c in courses for sem in (c.get("semesters") or [])})
        selected_offered_semesters = st.multiselect(
            "Offered in semesters (any overlap)",
            options=offered_sem_options,
            default=offered_sem_options,
        )
        query = st.text_input("Search by course code or name")

        col1, col2, col3 = st.columns(3)
        include_prereqs = col1.checkbox("Include prerequisite chain", value=True)
        hide_isolated = col2.checkbox("Hide isolated nodes", value=False)
        use_program_lens = col3.checkbox("Program lens (Major/Minor)", value=False)

        graph_structure = st.radio(
            "Transition emphasis",
            options=[
                "Year boxes with semester inside",
                "Semester-to-semester flow",
            ],
            horizontal=True,
            key="catalog_graph_structure",
        )

        clarity_cfg = _graph_clarity_controls("catalog", default_layout="Tree", student_mode=student_mode)

        if use_program_lens and program_index:
            major_subjects = sorted({subject for (subject, p_type) in program_index if p_type == "Major"})
            minor_subjects = sorted({subject for (subject, p_type) in program_index if p_type == "Minor"})

            if major_subjects and minor_subjects:
                major_key = "catalog_lens_major_subject"
                minor_key = "catalog_lens_minor_subject"
                if major_key not in st.session_state or st.session_state[major_key] not in major_subjects:
                    st.session_state[major_key] = major_subjects[0]
                if minor_key not in st.session_state or st.session_state[minor_key] not in minor_subjects:
                    default_minor = next((s for s in minor_subjects if s != st.session_state[major_key]), minor_subjects[0])
                    st.session_state[minor_key] = default_minor

                st.markdown("**Major lens**")
                m1, m2, m3 = st.columns([1, 4, 1])
                if m1.button("←", key="catalog_lens_prev_major"):
                    idx = major_subjects.index(st.session_state[major_key])
                    st.session_state[major_key] = major_subjects[(idx - 1) % len(major_subjects)]
                    _force_rerun()
                major_subject = m2.selectbox("Major subject", options=major_subjects, key=major_key)
                if m3.button("→", key="catalog_lens_next_major"):
                    idx = major_subjects.index(st.session_state[major_key])
                    st.session_state[major_key] = major_subjects[(idx + 1) % len(major_subjects)]
                    _force_rerun()

                st.markdown("**Minor lens**")
                n1, n2, n3 = st.columns([1, 4, 1])
                if n1.button("←", key="catalog_lens_prev_minor"):
                    idx = minor_subjects.index(st.session_state[minor_key])
                    st.session_state[minor_key] = minor_subjects[(idx - 1) % len(minor_subjects)]
                    _force_rerun()
                minor_subject = n2.selectbox("Minor subject", options=minor_subjects, key=minor_key)
                if n3.button("→", key="catalog_lens_next_minor"):
                    idx = minor_subjects.index(st.session_state[minor_key])
                    st.session_state[minor_key] = minor_subjects[(idx + 1) % len(minor_subjects)]
                    _force_rerun()

                major_criteria = program_index.get((major_subject, "Major"))
                minor_criteria = program_index.get((minor_subject, "Minor"))
                if major_criteria and minor_criteria:
                    focus_codes = set(cg.collect_requirement_codes(major_criteria)).union(
                        set(cg.collect_requirement_codes(minor_criteria))
                    )
                    st.caption(f"Lens active: {major_subject} Major + {minor_subject} Minor")
            else:
                st.info("No valid major/minor subject options found.")

    filtered = cg.filter_courses(courses, selected_subjects, selected_kinds, sem_range, query)

    selected_years_set = set(selected_years or [])
    if selected_years_set:
        filtered = [
            c for c in filtered
            if cg.course_year(c) in selected_years_set
        ]

    selected_sem_set = set(selected_offered_semesters or [])
    if selected_sem_set:
        filtered = [
            c for c in filtered
            if selected_sem_set.intersection(set(c.get("semesters") or []))
        ]

    if focus_codes is not None:
        filtered = [c for c in filtered if c.get("course_code") in focus_codes]

    if include_prereqs and filtered:
        filtered = cg.expand_with_prereqs(filtered, course_index)

    if hide_isolated and filtered:
        filtered = cg.remove_isolated_courses(filtered)

    if not filtered:
        st.warning("No courses match current filters")
        return

    if graph_structure == "Semester-to-semester flow":
        nodes, edges = cg.make_semester_graph_elements(filtered)
        selected_group_prefixes = ["group_sem_"]
    else:
        nodes, edges = cg.make_year_semester_graph_elements(filtered)
        selected_group_prefixes = ["group_catalog_year_"]

    display_edges = _filtered_edges_for_mode(edges, course_index, clarity_cfg["edge_mode"])
    nodes, display_edges = _apply_graph_visual_profile(
        nodes,
        display_edges,
        course_index,
        visual_mode=clarity_cfg["visual_mode"],
        label_mode=clarity_cfg["label_mode"],
    )

    visible_courses = len([n for n in nodes if not n.id.startswith("group_")])
    visible_sem_groups = len(
        [
            n for n in nodes
            if n.id.startswith("group_sem_") or (n.id.startswith("group_catalog_year_") and "_sem_" in n.id)
        ]
    )
    visible_year_groups = len({cg.course_year(c) for c in filtered if cg.course_year(c) is not None})
    visible_edges = len(display_edges)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Courses visible", visible_courses)
    c2.metric("Year groups", visible_year_groups)
    c3.metric("Semester groups", visible_sem_groups)
    c4.metric("Prerequisite links", visible_edges)

    pair_57_rows = _semester_pair_rows(filtered, (5, 7))
    pair_68_rows = _semester_pair_rows(filtered, (6, 8))
    p1, p2 = st.columns(2)
    p1.metric("Courses in both 5 & 7", len(pair_57_rows))
    p2.metric("Courses in both 6 & 8", len(pair_68_rows))

    with st.expander("Semester Pair Offerings (5&7 and 6&8)"):
        left, right = st.columns(2)
        with left:
            st.markdown("**Offered in both Semester 5 and 7**")
            if pair_57_rows:
                _show_df(pair_57_rows, use_container_width=True)
            else:
                st.info("No matching courses in current filtered view.")
        with right:
            st.markdown("**Offered in both Semester 6 and 8**")
            if pair_68_rows:
                _show_df(pair_68_rows, use_container_width=True)
            else:
                st.info("No matching courses in current filtered view.")

    _render_color_legend(
        "Catalog color guide",
        [
            ("Normal", cg.COURSE_KIND_COLOR_MAP.get("normal", "#2563eb")),
            ("Lab", cg.COURSE_KIND_COLOR_MAP.get("lab", "#0f766e")),
            ("Semester project", cg.COURSE_KIND_COLOR_MAP.get("semester_project", "#d97706")),
        ],
    )
    _render_graph_support_tables(
        distribution_title="Year/Semester Distribution",
        course_codes=[c.get("course_code") for c in filtered if c.get("course_code")],
        edges=display_edges,
        course_index=course_index,
        expanded=False,
    )

    widget = StreamlitGraphWidget(
        nodes=nodes,
        edges=display_edges,
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id",
        node_scale_factor_mapping="visual_scale",
        edge_thickness_factor_mapping="edge_scale",
        directed_mapping="directed",
    )
    selected_nodes, _ = _safe_show_graph(
        widget,
        graph_layout=clarity_cfg["layout"],
        key="catalog_graph_widget",
        directed=True,
        sync_selection=True,
        sidebar={"enabled": True},
    )

    st.markdown(
        """
        <div class="selection-panel">
            Click one or more course nodes to inspect details below.
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_codes = _selected_graph_course_codes(
        selected_nodes,
        group_prefixes=selected_group_prefixes,
    )
    if selected_codes:
        _show_df(
            _selected_course_detail_rows(selected_codes, course_index),
            use_container_width=True,
        )
    else:
        st.info("No course selected yet. Click a course node in the map.")

    if use_program_lens and focus_codes:
        missing_from_view = sorted([code for code in focus_codes if code not in {c.get("course_code") for c in filtered}])
        with st.expander("Lens courses not visible in current filters"):
            if missing_from_view:
                _show_df(_course_rows(missing_from_view, course_index), use_container_width=True)
            else:
                st.success("All program-lens courses are visible in current map.")


def _render_program_roadmap(program_index, course_index):
    st.subheader("Major/Minor Roadmap Graph")
    st.caption("Pick a program to see Year 1 to Year 4 pathway with prerequisites linked.")
    student_mode = _is_student_mode()

    if not program_index:
        st.info("No major/minor program rules loaded")
        return

    subject, p_type = _subject_type_selector(program_index, "roadmap")
    if not subject or not p_type:
        st.info("No program selection available")
        return

    criteria = program_index[(subject, p_type)]

    view_mode = st.selectbox(
        "Requirement view",
        options=[
            "Compulsory + elective options",
            "Compulsory only",
            "Complete (including not-counted)",
        ],
        key="roadmap_requirement_view",
    )
    if view_mode == "Compulsory only":
        selected_sets = ["set_d"]
    elif view_mode == "Complete (including not-counted)":
        selected_sets = list(SET_ORDER)
    else:
        selected_sets = ["set_a", "set_b", "set_c", "set_d"]

    col1, col2, _ = st.columns(3)
    include_prereq_support = col1.checkbox(
        "Add support prerequisites",
        value=True,
        help="Also show prerequisite courses that are not explicitly listed in rule sets.",
    )
    year_range = col2.slider("Year range", min_value=1, max_value=4, value=(1, 4))
    clarity_cfg = _graph_clarity_controls("roadmap", default_layout="Orthogonal", student_mode=student_mode)

    roadmap = cg.make_program_roadmap_elements(
        criteria,
        course_index,
        include_prereq_support=include_prereq_support,
        selected_sets=selected_sets,
        year_range=year_range,
    )

    nodes = roadmap["nodes"]
    edges = roadmap["edges"]
    display_edges = _filtered_edges_for_mode(edges, course_index, clarity_cfg["edge_mode"])
    nodes, display_edges = _apply_graph_visual_profile(
        nodes,
        display_edges,
        course_index,
        visual_mode=clarity_cfg["visual_mode"],
        label_mode=clarity_cfg["label_mode"],
    )

    if not nodes or len([n for n in nodes if not n.id.startswith("group_year_")]) == 0:
        st.warning("No roadmap courses available for this selection")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Program courses found", len(roadmap["base_codes_present"]))
    c2.metric("Program courses missing", len(roadmap["base_codes_missing"]))
    c3.metric("Visible courses", len([n for n in nodes if not n.id.startswith("group_year_")]))
    c4.metric("Prerequisite links", len(display_edges))

    if roadmap["base_codes_missing"]:
        st.warning("Some rule-list courses are missing from catalog data")
        _show_df(
            {"missing_course_codes": roadmap["base_codes_missing"]},
            use_container_width=True,
        )

    _render_color_legend(
        "Roadmap color guide",
        [
            ("Compulsory", cg.SET_COLOR_MAP.get("set_d", "#d1495b")),
            ("Elective pool", cg.SET_COLOR_MAP.get("set_a", "#0077b6")),
            ("Capped pool", cg.SET_COLOR_MAP.get("set_b", "#f4a261")),
            ("Supplementary", cg.SET_COLOR_MAP.get("set_c", "#2a9d8f")),
            ("Not counted", cg.SET_COLOR_MAP.get("set_e", "#8d99ae")),
            ("Support prereq", cg.SET_COLOR_MAP.get("support", "#6c757d")),
        ],
    )

    _render_graph_support_tables(
        distribution_title="Roadmap Year/Semester Distribution",
        course_codes=roadmap["visible_codes"],
        edges=display_edges,
        course_index=course_index,
        expanded=False,
    )

    widget = StreamlitGraphWidget(
        nodes=nodes,
        edges=display_edges,
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id",
        node_scale_factor_mapping="visual_scale",
        edge_thickness_factor_mapping="edge_scale",
        directed_mapping="directed",
    )
    selected_nodes, _ = _safe_show_graph(
        widget,
        graph_layout=clarity_cfg["layout"],
        key="roadmap_graph_widget",
        directed=True,
        sync_selection=True,
        sidebar={"enabled": True},
    )

    st.markdown(
        """
        <div class="selection-panel">
            Click course nodes in the graph to inspect them below.
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_codes = _selected_graph_course_codes(selected_nodes, group_prefixes=["group_year_"])
    if selected_codes:
        label_lookup = {code: {label} for code, label in _code_requirement_label_lookup(criteria).items()}
        _show_df(
            _selected_course_detail_rows(
                selected_codes,
                course_index,
                set_lookup=label_lookup,
            ),
            use_container_width=True,
        )
    else:
        st.info("No course selected yet. Click one or more course nodes in the roadmap graph.")


def _render_student_planner(program_index, course_index, constraints):
    st.subheader("Student Planner")
    st.caption("Track progress to 184 credits by Semester 8 while balancing major and minor requirements.")
    student_mode = _is_student_mode()

    st.markdown(
        """
        <div class="planner-note">
            Practical mode: choose one major and one minor, enter completed courses, and get a constrained semester plan.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not program_index:
        st.info("No major/minor program rules loaded")
        return

    degree_target = int((constraints or {}).get("min_degree_credits", 184) or 184)
    total_semesters = int((constraints or {}).get("num_semesters", 8) or 8)

    major_subjects = sorted({s for (s, t) in program_index if t == "Major"})
    minor_subjects = sorted({s for (s, t) in program_index if t == "Minor"})

    if not major_subjects or not minor_subjects:
        st.warning("Major/minor options are incomplete in current requirements file")
        return

    c1, c2 = st.columns(2)
    major_subject = c1.selectbox("Major subject", major_subjects, key="planner_major_subject")

    minor_default = next((s for s in minor_subjects if s != major_subject), minor_subjects[0])
    minor_index = minor_subjects.index(minor_default)
    minor_subject = c2.selectbox(
        "Minor subject",
        minor_subjects,
        index=minor_index,
        key="planner_minor_subject",
    )

    if major_subject == minor_subject:
        st.warning("Major and minor are currently the same subject. Choose different subjects for a broader pathway.")

    major_criteria = program_index.get((major_subject, "Major"))
    minor_criteria = program_index.get((minor_subject, "Minor"))
    if not major_criteria or not minor_criteria:
        st.error("Could not load selected major/minor criteria")
        return

    p1, p2, p3 = st.columns(3)
    current_semester = p1.slider(
        "Current semester",
        min_value=1,
        max_value=total_semesters,
        value=1,
        key="planner_current_semester",
    )
    max_courses_per_term = p2.slider(
        "Max courses per term",
        min_value=1,
        max_value=8,
        value=4,
        key="planner_max_courses",
    )
    max_credits_per_term = p3.slider(
        "Max credits per term",
        min_value=8,
        max_value=32,
        value=24,
        key="planner_max_credits",
    )

    major_requirement_codes = cg.collect_requirement_codes(major_criteria)
    minor_requirement_codes = cg.collect_requirement_codes(minor_criteria)
    combined_requirement_codes = sorted(major_requirement_codes.union(minor_requirement_codes))

    foundation_seed = [code for code in _foundation_compulsory_codes(constraints, upto_semester=3) if code in course_index]
    suggested_major = cg.parse_pathway(cg.suggest_pathway(major_criteria, limit=12))
    suggested_minor = cg.parse_pathway(cg.suggest_pathway(minor_criteria, limit=8))
    default_seed_codes = list(dict.fromkeys(foundation_seed + suggested_major + suggested_minor))
    default_seed = ", ".join(default_seed_codes)

    if foundation_seed:
        with st.expander("Auto-included common Sem 1-3 compulsory courses", expanded=False):
            _show_df(_course_rows(foundation_seed, course_index), use_container_width=True)
    state_key = "planner_completed_courses"
    if state_key not in st.session_state:
        st.session_state[state_key] = default_seed

    st.markdown("#### Update Planner Courses")
    st.markdown(
        """
        <div class="soft-panel">
            Use quick controls to update your course list, then fine-tune in the raw text box below.
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_state_courses = cg.parse_pathway(st.session_state[state_key])
    quick_options = sorted(set(combined_requirement_codes).union(current_state_courses))
    quick_selected = st.multiselect(
        "Quick updater (major + minor requirement codes)",
        options=quick_options,
        default=current_state_courses,
        key="planner_quick_updater",
    )

    u1, u2, u3 = st.columns(3)
    if u1.button("Apply quick update", key="planner_apply_quick_update"):
        st.session_state[state_key] = ", ".join(quick_selected)
        _force_rerun()

    if u2.button("Add all major+minor requirement codes", key="planner_add_all_requirements"):
        merged = sorted(set(current_state_courses).union(combined_requirement_codes))
        st.session_state[state_key] = ", ".join(merged)
        _force_rerun()

    if u3.button("Clear planner input", key="planner_clear_input"):
        st.session_state[state_key] = ""
        _force_rerun()

    raw_courses = st.text_area(
        "Completed or planned courses",
        height=120,
        key=state_key,
    )
    parsed_courses = cg.parse_pathway(raw_courses)
    known_courses = [code for code in parsed_courses if code in course_index]
    unknown_courses = [code for code in parsed_courses if code not in course_index]

    earned_credits = sum((course_index[code].get("credits", 0) for code in known_courses))
    remaining_credits = max(0, degree_target - earned_credits)
    semesters_left = max(1, total_semesters - current_semester + 1)
    avg_needed = round(remaining_credits / semesters_left, 2)
    credit_feasible = earned_credits + semesters_left * max_credits_per_term >= degree_target

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Degree credits earned", earned_credits)
    m2.metric("Remaining to degree", remaining_credits)
    m3.metric("Semesters left", semesters_left)
    m4.metric("Avg needed / semester", avg_needed)
    m5.metric("184 feasible", "Yes" if credit_feasible else "No")

    st.progress(min(1.0, earned_credits / max(1, degree_target)))
    st.caption(f"Progress: {earned_credits}/{degree_target} credits")

    input_edges = cg.build_edges_from_courses(known_courses, course_index)
    _render_graph_support_tables(
        distribution_title="Current Input Year/Semester Distribution",
        course_codes=known_courses,
        edges=input_edges,
        course_index=course_index,
        expanded=False,
    )
    if unknown_courses:
        st.warning("Unknown course codes in planner input: " + ", ".join(unknown_courses))

    credit_map = {code: c.get("credits", 0) for code, c in course_index.items()}
    major_result = validate_major_minor_pathway(known_courses, major_criteria, credit_map)
    minor_result = validate_major_minor_pathway(known_courses, minor_criteria, credit_map)

    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Major valid", "Yes" if major_result.get("is_valid") else "No")
    v2.metric("Minor valid", "Yes" if minor_result.get("is_valid") else "No")
    v3.metric("Major counted credits", major_result.get("total_credits", 0))
    v4.metric("Minor counted credits", minor_result.get("total_credits", 0))

    with st.expander("Major requirement gaps"):
        if major_result.get("errors"):
            for err in major_result["errors"]:
                st.markdown(f"- {err}")
        else:
            st.success("No major requirement violations for current input")

    with st.expander("Minor requirement gaps"):
        if minor_result.get("errors"):
            for err in minor_result["errors"]:
                st.markdown(f"- {err}")
        else:
            st.success("No minor requirement violations for current input")

    st.markdown("#### Requirement Category Progress")
    s1, s2 = st.columns(2)
    with s1:
        st.markdown(f"**{major_subject} Major**")
        mb = major_result.get("set_breakdown", {}) or {}
        _show_df(
            [
                {
                    "Category": "Compulsory",
                    "Satisfied": "Yes" if mb.get("set_d", {}).get("is_satisfied") else "No",
                    "Taken": mb.get("set_d", {}).get("taken_count", 0),
                    "Rule check": f"missing {len(mb.get('set_d', {}).get('missing_required', []))}",
                },
                {
                    "Category": "Elective options",
                    "Satisfied": "Yes" if (mb.get("set_a", {}).get("is_satisfied", True) and mb.get("set_b", {}).get("is_satisfied", True)) else "No",
                    "Taken": (
                        mb.get("set_a", {}).get("taken_count", 0)
                        + mb.get("set_b", {}).get("taken_count", 0)
                        + mb.get("set_c", {}).get("taken_count", 0)
                    ),
                    "Rule check": (
                        f"min target {mb.get('set_a', {}).get('required_min', 0)}"
                        if mb.get("set_a", {}).get("is_configured")
                        else "no minimum target"
                    ),
                },
            ],
            use_container_width=True,
        )
    with s2:
        st.markdown(f"**{minor_subject} Minor**")
        nb = minor_result.get("set_breakdown", {}) or {}
        _show_df(
            [
                {
                    "Category": "Compulsory",
                    "Satisfied": "Yes" if nb.get("set_d", {}).get("is_satisfied") else "No",
                    "Taken": nb.get("set_d", {}).get("taken_count", 0),
                    "Rule check": f"missing {len(nb.get('set_d', {}).get('missing_required', []))}",
                },
                {
                    "Category": "Elective options",
                    "Satisfied": "Yes" if (nb.get("set_a", {}).get("is_satisfied", True) and nb.get("set_b", {}).get("is_satisfied", True)) else "No",
                    "Taken": (
                        nb.get("set_a", {}).get("taken_count", 0)
                        + nb.get("set_b", {}).get("taken_count", 0)
                        + nb.get("set_c", {}).get("taken_count", 0)
                    ),
                    "Rule check": (
                        f"min target {nb.get('set_a', {}).get('required_min', 0)}"
                        if nb.get("set_a", {}).get("is_configured")
                        else "no minimum target"
                    ),
                },
            ],
            use_container_width=True,
        )

    major_remaining_rows = _not_selected_requirement_rows(
        major_criteria,
        known_courses,
        course_index,
        program_label=f"{major_subject} Major",
    )
    minor_remaining_rows = _not_selected_requirement_rows(
        minor_criteria,
        known_courses,
        course_index,
        program_label=f"{minor_subject} Minor",
    )

    st.markdown("#### Requirement Courses Not Yet Selected")
    remaining_rows = major_remaining_rows + minor_remaining_rows
    if remaining_rows:
        _show_df(remaining_rows, use_container_width=True)
    else:
        st.success("All listed major/minor requirement courses are in your current planner input.")

    combined_nodes, combined_edges, combined_graph, combined_role_lookup = _major_minor_combined_elements(
        major_criteria=major_criteria,
        minor_criteria=minor_criteria,
        course_index=course_index,
        include_prereq_support=True,
        year_range=(1, 4),
    )

    major_compulsory = set(cg.requirement_codes_by_set(major_criteria).get("set_d", []))
    minor_compulsory = set(cg.requirement_codes_by_set(minor_criteria).get("set_d", []))
    priority_codes = major_compulsory.union(minor_compulsory)

    plan_payload = cg.plan_courses_by_term(
        graph=combined_graph,
        course_index=course_index,
        start_semester=current_semester,
        max_courses_per_term=max_courses_per_term,
        max_terms=semesters_left,
        priority_codes=priority_codes,
        already_completed=known_courses,
        max_credits_per_term=max_credits_per_term,
    )

    st.markdown("#### Suggested Semester Plan")
    if plan_payload.get("plan"):
        rows = []
        cumulative = earned_credits
        for sem, codes in sorted(plan_payload["plan"].items()):
            sem_credits = sum((course_index.get(code, {}).get("credits", 0) for code in codes))
            cumulative += sem_credits
            rows.append(
                {
                    "year": ((sem - 1) // 2) + 1,
                    "semester": sem,
                    "term_type": "Odd" if sem % 2 == 1 else "Even",
                    "courses": ", ".join(codes),
                    "course_count": len(codes),
                    "semester_credits": sem_credits,
                    "projected_total_credits": cumulative,
                }
            )
        _show_df(rows, use_container_width=True)
    else:
        st.info("No schedule generated. Try increasing max courses/credits per term.")

    if plan_payload.get("blocked_details"):
        with st.expander("Blocked courses in planner"):
            _show_df(plan_payload["blocked_details"], use_container_width=True)

    st.markdown("#### Combined Major-Minor Dependency Graph")
    _render_color_legend(
        "Combined graph color guide",
        [
            ("Major", ROLE_COLOR_MAP["major"]),
            ("Minor", ROLE_COLOR_MAP["minor"]),
            ("Shared (both)", ROLE_COLOR_MAP["both"]),
            ("Support prereq", ROLE_COLOR_MAP["support"]),
        ],
    )

    planner_clarity_cfg = _graph_clarity_controls("planner", default_layout="Hierarchic", student_mode=student_mode)

    display_edges = _filtered_edges_for_mode(combined_edges, course_index, planner_clarity_cfg["edge_mode"])
    combined_nodes, display_edges = _apply_graph_visual_profile(
        combined_nodes,
        display_edges,
        course_index,
        visual_mode=planner_clarity_cfg["visual_mode"],
        label_mode=planner_clarity_cfg["label_mode"],
    )
    _render_graph_support_tables(
        distribution_title="Combined Graph Year/Semester Distribution",
        course_codes=list(combined_graph.nodes),
        edges=display_edges,
        course_index=course_index,
        expanded=False,
    )

    planner_widget = StreamlitGraphWidget(
        nodes=combined_nodes,
        edges=display_edges,
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id",
        node_scale_factor_mapping="visual_scale",
        edge_thickness_factor_mapping="edge_scale",
        directed_mapping="directed",
    )
    selected_nodes, _ = _safe_show_graph(
        planner_widget,
        graph_layout=planner_clarity_cfg["layout"],
        key="student_planner_graph_widget",
        directed=True,
        sync_selection=True,
        sidebar={"enabled": True},
    )

    st.markdown(
        """
        <div class="selection-panel">
            Click graph nodes to inspect course details and directly update your planner list.
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_codes = _selected_graph_course_codes(selected_nodes, group_prefixes=["group_combined_year_"])
    if selected_codes:
        major_set_lookup = cg.collect_code_to_sets(major_criteria)
        minor_set_lookup = cg.collect_code_to_sets(minor_criteria)
        merged_set_lookup = {}
        for mapping in [major_set_lookup, minor_set_lookup]:
            for code, sets in mapping.items():
                merged_set_lookup.setdefault(code, set()).update(sets)

        _show_df(
            _selected_course_detail_rows(
                selected_codes,
                course_index,
                set_lookup=merged_set_lookup,
                role_lookup=combined_role_lookup,
            ),
            use_container_width=True,
        )

        b1, b2 = st.columns(2)
        if b1.button("Add selected graph courses", key="planner_add_selected_graph_courses"):
            combined = list(parsed_courses)
            for code in selected_codes:
                if code not in combined:
                    combined.append(code)
            st.session_state[state_key] = ", ".join(combined)
            _force_rerun()

        if b2.button("Remove selected graph courses", key="planner_remove_selected_graph_courses"):
            selected_set = set(selected_codes)
            filtered = [code for code in parsed_courses if code not in selected_set]
            st.session_state[state_key] = ", ".join(filtered)
            _force_rerun()
    else:
        st.info("No course selected yet. Click one or more course nodes in the combined graph.")


def _render_combination_simulator(program_index, course_index, constraints):
    st.subheader("All Major-Minor Combination Simulator")
    st.caption(
        "Simulate all valid major-minor combinations using common Sem 1-3 compulsory courses and elective options."
    )
    student_mode = _is_student_mode()

    if not program_index:
        st.info("No major/minor program rules loaded")
        return

    major_subjects = sorted({subject for (subject, p_type) in program_index if p_type == "Major"})
    minor_subjects = sorted({subject for (subject, p_type) in program_index if p_type == "Minor"})
    if not major_subjects or not minor_subjects:
        st.warning("Major/minor options are incomplete in current requirements file")
        return

    foundation_codes = [code for code in _foundation_compulsory_codes(constraints, upto_semester=3) if code in course_index]

    sem3_group_options = []
    sem3_group_cap = None
    for sem_block in (constraints or {}).get("semesters", []):
        if int(sem_block.get("semester_number", 0) or 0) == 3:
            max_group = sem_block.get("max_group") or {}
            sem3_group_options = [code for code in (max_group.get("available_courses") or []) if code in course_index]
            sem3_group_cap = max_group.get("max_allowed")

    s1, s2, s3 = st.columns(3)
    start_semester = s1.slider("Simulation start semester", min_value=4, max_value=8, value=4, key="sim_start_sem")
    max_courses_per_term = s2.slider("Max courses per term", min_value=1, max_value=8, value=4, key="sim_max_courses")
    max_credits_per_term = s3.slider("Max credits per term", min_value=8, max_value=32, value=24, key="sim_max_credits")

    selected_sem3_electives = []
    if sem3_group_options:
        selected_sem3_electives = st.multiselect(
            f"Semester 3 elective choices (recommended max {sem3_group_cap})",
            options=sem3_group_options,
            default=sem3_group_options[: int(sem3_group_cap or 0)],
            key="sim_sem3_electives",
        )

    base_completed = list(dict.fromkeys(foundation_codes + selected_sem3_electives))
    with st.expander("Base completed courses used for simulation", expanded=False):
        _show_df(_course_rows(base_completed, course_index), use_container_width=True)

    total_semesters = int((constraints or {}).get("num_semesters", 8) or 8)
    max_terms = max(1, total_semesters - int(start_semester) + 1)

    combo_rows = []
    combo_index = {}
    for major_subject in major_subjects:
        major_criteria = program_index.get((major_subject, "Major"))
        if not major_criteria:
            continue

        major_buckets = _friendly_requirement_buckets(major_criteria)
        for minor_subject in minor_subjects:
            minor_criteria = program_index.get((minor_subject, "Minor"))
            if not minor_criteria:
                continue

            minor_buckets = _friendly_requirement_buckets(minor_criteria)

            major_sel = cg.collect_program_codes(
                criteria=major_criteria,
                course_index=course_index,
                selected_sets=["set_a", "set_b", "set_c", "set_d"],
                include_prereq_support=True,
                year_range=(1, 4),
            )
            minor_sel = cg.collect_program_codes(
                criteria=minor_criteria,
                course_index=course_index,
                selected_sets=["set_a", "set_b", "set_c", "set_d"],
                include_prereq_support=True,
                year_range=(1, 4),
            )

            combined_codes = set(major_sel["visible_codes"]).union(set(minor_sel["visible_codes"]))
            combined_graph = cg.build_dependency_digraph(course_index, combined_codes)

            compulsory_codes = set(major_buckets["compulsory"]).union(set(minor_buckets["compulsory"]))
            elective_codes = set(major_buckets["electives"]).union(set(minor_buckets["electives"]))

            plan = cg.plan_courses_by_term(
                graph=combined_graph,
                course_index=course_index,
                start_semester=start_semester,
                max_courses_per_term=max_courses_per_term,
                max_terms=max_terms,
                priority_codes=compulsory_codes,
                already_completed=base_completed,
                max_credits_per_term=max_credits_per_term,
            )

            pair57_count = 0
            pair68_count = 0
            for code in elective_codes:
                semesters = set(course_index.get(code, {}).get("semesters", []) or [])
                if {5, 7}.issubset(semesters):
                    pair57_count += 1
                if {6, 8}.issubset(semesters):
                    pair68_count += 1

            scheduled_codes = set(plan.get("scheduled", []))
            projected_credits = sum(
                int(course_index.get(code, {}).get("credits", 0) or 0)
                for code in scheduled_codes.union(set(base_completed))
            )

            combo_label = f"{major_subject} Major + {minor_subject} Minor"
            combo_index[combo_label] = {
                "major_subject": major_subject,
                "minor_subject": minor_subject,
                "major_criteria": major_criteria,
                "minor_criteria": minor_criteria,
                "plan": plan,
                "base_completed": base_completed,
                "compulsory_codes": sorted(compulsory_codes),
                "elective_codes": sorted(elective_codes),
            }

            combo_rows.append(
                {
                    "Combination": combo_label,
                    "Major": major_subject,
                    "Minor": minor_subject,
                    "Compulsory": len(compulsory_codes),
                    "Elective options": len(elective_codes),
                    "Sem 5&7 options": pair57_count,
                    "Sem 6&8 options": pair68_count,
                    "Blocked": len(plan.get("blocked", [])),
                    "Plan complete": "Yes" if plan.get("is_complete") else "No",
                    "Projected credits": projected_credits,
                }
            )

    if not combo_rows:
        st.warning("No combinations could be simulated.")
        return

    combo_rows.sort(key=lambda row: (row["Plan complete"] != "Yes", row["Blocked"], row["Combination"]))
    _show_df(combo_rows, use_container_width=True)

    selected_combo = st.selectbox("Inspect a combination", [row["Combination"] for row in combo_rows], key="sim_combo_select")
    combo_payload = combo_index[selected_combo]

    st.markdown("#### Combination Details")
    d1, d2, d3 = st.columns(3)
    d1.metric("Compulsory courses", len(combo_payload["compulsory_codes"]))
    d2.metric("Elective options", len(combo_payload["elective_codes"]))
    d3.metric("Blocked courses", len(combo_payload["plan"].get("blocked", [])))

    with st.expander("Compulsory courses in this combination", expanded=False):
        _show_df(_course_rows(combo_payload["compulsory_codes"], course_index), use_container_width=True)

    with st.expander("Elective options in this combination", expanded=False):
        _show_df(_course_rows(combo_payload["elective_codes"], course_index), use_container_width=True)

    st.markdown("#### Suggested Plan for Selected Combination")
    if combo_payload["plan"].get("plan"):
        rows = []
        for sem, codes in sorted(combo_payload["plan"]["plan"].items()):
            rows.append(
                {
                    "year": ((sem - 1) // 2) + 1,
                    "semester": sem,
                    "term_type": "Odd" if sem % 2 == 1 else "Even",
                    "courses": ", ".join(codes),
                    "course_count": len(codes),
                    "credits": sum(int(course_index.get(code, {}).get("credits", 0) or 0) for code in codes),
                }
            )
        _show_df(rows, use_container_width=True)
    else:
        st.info("No feasible plan generated for this combination with current simulation constraints.")

    sim_nodes, sim_edges, _, sim_role_lookup = _major_minor_combined_elements(
        major_criteria=combo_payload["major_criteria"],
        minor_criteria=combo_payload["minor_criteria"],
        course_index=course_index,
        include_prereq_support=True,
        year_range=(1, 4),
    )

    st.markdown("#### Combination Dependency Graph")
    _render_color_legend(
        "Combination graph color guide",
        [
            ("Major", ROLE_COLOR_MAP["major"]),
            ("Minor", ROLE_COLOR_MAP["minor"]),
            ("Shared (both)", ROLE_COLOR_MAP["both"]),
            ("Support prereq", ROLE_COLOR_MAP["support"]),
        ],
    )
    sim_clarity_cfg = _graph_clarity_controls("sim_combo", default_layout="Hierarchic", student_mode=student_mode)

    display_edges = _filtered_edges_for_mode(sim_edges, course_index, sim_clarity_cfg["edge_mode"])
    sim_nodes, display_edges = _apply_graph_visual_profile(
        sim_nodes,
        display_edges,
        course_index,
        visual_mode=sim_clarity_cfg["visual_mode"],
        label_mode=sim_clarity_cfg["label_mode"],
    )
    _render_graph_support_tables(
        distribution_title="Combination Graph Year/Semester Distribution",
        course_codes=list(code for code in combo_payload["plan"].get("scheduled", [])),
        edges=display_edges,
        course_index=course_index,
        expanded=False,
    )

    sim_widget = StreamlitGraphWidget(
        nodes=sim_nodes,
        edges=display_edges,
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id",
        node_scale_factor_mapping="visual_scale",
        edge_thickness_factor_mapping="edge_scale",
        directed_mapping="directed",
    )
    selected_nodes, _ = _safe_show_graph(
        sim_widget,
        graph_layout=sim_clarity_cfg["layout"],
        key="sim_combo_graph_widget",
        directed=True,
        sync_selection=True,
        sidebar={"enabled": True},
    )

    picked_codes = _selected_graph_course_codes(selected_nodes, group_prefixes=["group_combined_year_"])
    if picked_codes:
        label_lookup = {}
        label_lookup.update({code: "Compulsory" for code in combo_payload["compulsory_codes"]})
        label_lookup.update({code: "Elective option" for code in combo_payload["elective_codes"]})
        _show_df(
            _selected_course_detail_rows(
                picked_codes,
                course_index,
                set_lookup=label_lookup,
                role_lookup=sim_role_lookup,
            ),
            use_container_width=True,
        )
    else:
        st.info("Click course nodes in this graph to inspect details.")


def _render_pathway_algorithms(program_index, course_index):
    st.subheader("Directed Dependency Planning")
    st.caption(
        "Run cycle checks, topological ordering, representative pathways, and a constrained plan by semester."
    )

    if not program_index:
        st.info("No major/minor program rules loaded")
        return

    subject, p_type = _subject_type_selector(program_index, "algorithms")
    if not subject or not p_type:
        st.info("No program selection available")
        return

    criteria = program_index[(subject, p_type)]

    view_mode = st.selectbox(
        "Requirement view",
        options=[
            "Compulsory + elective options",
            "Compulsory only",
            "Complete (including not-counted)",
        ],
        key="algo_requirement_view",
    )
    if view_mode == "Compulsory only":
        selected_sets = ["set_d"]
    elif view_mode == "Complete (including not-counted)":
        selected_sets = list(SET_ORDER)
    else:
        selected_sets = ["set_a", "set_b", "set_c", "set_d"]

    c1, c2, c3, c4 = st.columns(4)
    include_prereq_support = c1.checkbox("Add support prerequisites", value=True, key="algo_support")
    year_range = c2.slider("Year range", min_value=1, max_value=4, value=(1, 4), key="algo_years")
    start_semester = c3.slider("Starting semester", min_value=1, max_value=8, value=1, key="algo_start")
    max_courses_per_term = c4.slider("Max courses per term", min_value=1, max_value=8, value=4, key="algo_load")
    max_terms = st.slider("Planning horizon (terms)", min_value=2, max_value=12, value=8, key="algo_terms")

    analysis = cg.build_program_dependency_analysis(
        criteria=criteria,
        course_index=course_index,
        selected_sets=selected_sets,
        include_prereq_support=include_prereq_support,
        year_range=year_range,
        start_semester=start_semester,
        max_courses_per_term=max_courses_per_term,
        max_terms=max_terms,
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Nodes", analysis["node_count"])
    m2.metric("Directed edges", analysis["edge_count"])
    m3.metric("DAG", "Yes" if analysis["is_dag"] else "No")
    m4.metric("Cycles", len(analysis["cycles"]))
    m5.metric("Blocked in plan", len(analysis["plan"].get("blocked", [])))

    reachability = analysis.get("reachability", {})
    starters = reachability.get("starters", [])
    unreachable = reachability.get("unreachable", [])
    r1, r2 = st.columns(2)
    r1.metric("Start-feasible nodes", len(starters))
    r2.metric("Unreachable nodes", len(unreachable))

    if analysis["base_codes_missing"]:
        st.warning(
            "Program contains codes missing in catalog: " + ", ".join(analysis["base_codes_missing"])
        )

    if analysis["cycles"]:
        st.error("Cycle(s) detected in prerequisite graph; topological sorting and strict planning may fail.")
        cycle_rows = [{"cycle": " -> ".join(c + [c[0]])} for c in analysis["cycles"]]
        _show_df(cycle_rows, use_container_width=True)

    st.markdown("#### Topological Order")
    topo = analysis["topological_order"]
    if topo:
        _show_df(
            [{"position": idx + 1, "course_code": code} for idx, code in enumerate(topo)],
            use_container_width=True,
        )
    else:
        st.info("No topological order available (likely due to cycle or empty selection).")

    st.markdown("#### Constrained Term Plan")
    plan_payload = analysis["plan"]
    if plan_payload.get("plan"):
        plan_rows = []
        for semester, codes in sorted(plan_payload["plan"].items()):
            credits = sum((course_index.get(code, {}).get("credits", 0) for code in codes))
            plan_rows.append(
                {
                    "semester": semester,
                    "courses": ", ".join(codes),
                    "course_count": len(codes),
                    "credits": credits,
                }
            )
        _show_df(plan_rows, use_container_width=True)
    else:
        st.info("No courses could be scheduled with current constraints.")

    if plan_payload.get("blocked_details"):
        with st.expander("Blocked courses details"):
            _show_df(plan_payload["blocked_details"], use_container_width=True)

    if unreachable:
        with st.expander("Unreachable nodes details"):
            _show_df({"course_code": unreachable}, use_container_width=True)

    st.markdown("#### Representative Paths to Completion Courses")
    rep_paths = analysis["representative_paths"]
    if rep_paths:
        rows = []
        for target, paths in rep_paths.items():
            for idx, path in enumerate(paths, start=1):
                rows.append(
                    {
                        "target": target,
                        "path_rank": idx,
                        "path": " -> ".join(path),
                        "length": len(path),
                    }
                )
        _show_df(rows, use_container_width=True)
    else:
        st.info("No representative paths available for current selection.")

    st.markdown("#### Bottleneck Courses")
    bottlenecks = analysis["bottlenecks"]
    if bottlenecks:
        _show_df(bottlenecks, use_container_width=True)
    else:
        st.info("No bottleneck analytics available for current selection.")

    st.markdown("#### Directed Program Dependency Graph")
    roadmap = cg.make_program_roadmap_elements(
        criteria,
        course_index,
        include_prereq_support=include_prereq_support,
        selected_sets=selected_sets,
        year_range=year_range,
    )
    algo_clarity_cfg = _graph_clarity_controls("algorithms", default_layout="Hierarchic")

    display_edges = _filtered_edges_for_mode(roadmap["edges"], course_index, algo_clarity_cfg["edge_mode"])
    roadmap_nodes, display_edges = _apply_graph_visual_profile(
        roadmap["nodes"],
        display_edges,
        course_index,
        visual_mode=algo_clarity_cfg["visual_mode"],
        label_mode=algo_clarity_cfg["label_mode"],
    )

    widget = StreamlitGraphWidget(
        nodes=roadmap_nodes,
        edges=display_edges,
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id",
        node_scale_factor_mapping="visual_scale",
        edge_thickness_factor_mapping="edge_scale",
        directed_mapping="directed",
    )
    _safe_show_graph(
        widget,
        graph_layout=algo_clarity_cfg["layout"],
        key="algorithms_graph_widget",
        directed=True,
    )


def _render_rules(program_index, course_index):
    st.subheader("Program Rules Explorer")

    if not program_index:
        st.info("No major/minor program rules loaded")
        return

    subject, p_type = _subject_type_selector(program_index, "rules")
    if not subject or not p_type:
        st.info("No program selection available")
        return

    criteria = program_index[(subject, p_type)]
    overall = criteria.get("overall_requirements", {})
    buckets = _friendly_requirement_buckets(criteria)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Minimum total courses", overall.get("minimum_total_courses"))
    c2.metric("Minimum total credits", overall.get("minimum_total_credits"))
    c3.metric("Compulsory", len(buckets["compulsory"]))
    c4.metric("Elective options", len(buckets["electives"]))
    c5.metric("Not counted", len(buckets["excluded"]))

    st.markdown("#### Requirement Categories")

    unknown_codes = sorted([code for code in cg.collect_requirement_codes(criteria) if code not in course_index])
    if unknown_codes:
        st.warning("Unknown codes in requirement list: " + ", ".join(unknown_codes))

    for heading, codes in [
        ("Compulsory Courses", buckets["compulsory"]),
        ("Elective Options", buckets["electives"]),
        ("Not Counted", buckets["excluded"]),
    ]:
        st.markdown(f"#### {heading}")
        if codes:
            _show_df(_course_rows(codes, course_index), use_container_width=True)
        else:
            st.info("No courses in this category for current program.")

    st.caption("Rule definitions above are production-facing summaries of the active program criteria.")

def _render_validation(program_index, course_index):
    st.subheader("Pathway Validation")
    st.caption("Enter course codes separated by comma/space/newline/semicolon")

    if not program_index:
        st.info("No major/minor program rules loaded")
        return

    subject, p_type = _subject_type_selector(program_index, "validate")
    if not subject or not p_type:
        st.info("No program selection available")
        return

    criteria = program_index[(subject, p_type)]

    state_key = f"validate_{subject}_{p_type}".replace(" ", "_")
    if state_key not in st.session_state:
        st.session_state[state_key] = cg.suggest_pathway(criteria)

    s1, s2 = st.columns([1, 3])
    if s1.button("Load sample", key=f"load_{state_key}"):
        st.session_state[state_key] = cg.suggest_pathway(criteria)
        _force_rerun()
    s2.caption("Edit sample and click validate")

    raw_text = st.text_area("Pathway", key=state_key, height=140)
    pathway = cg.parse_pathway(raw_text)

    known_codes = set(course_index.keys())
    unknown_codes = [code for code in pathway if code not in known_codes]

    rows = []
    for code in pathway:
        course = course_index.get(code)
        rows.append(
            {
                "Code": code,
                "Known": bool(course),
                "Course Name": course.get("course_name") if course else "(unknown)",
                "Credits": course.get("credits") if course else 0,
                "Subject": course.get("subject") if course else "-",
            }
        )

    m1, m2 = st.columns(2)
    m1.metric("Parsed courses", len(pathway))
    m2.metric("Unknown codes", len(unknown_codes))
    if rows:
        _show_df(rows, use_container_width=True)

    if unknown_codes:
        st.warning("Unknown codes in pathway: " + ", ".join(unknown_codes))

    if st.button("Validate", type="primary", key=f"submit_{state_key}"):
        if not pathway:
            st.error("Enter at least one course code")
            return

        course_credits_map = {code: c.get("credits", 0) for code, c in course_index.items()}
        result = validate_major_minor_pathway(pathway, criteria, course_credits_map)

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Is valid", "Yes" if result.get("is_valid") else "No")
        r2.metric("Counted courses", result.get("total_courses", 0))
        r3.metric("Counted credits", result.get("total_credits", 0))
        r4.metric("Excluded by Set E", len(result.get("excluded_by_set_e", [])))

        if result.get("unknown_courses"):
            st.warning(
                "Unknown codes not found in course credit map: " + ", ".join(result["unknown_courses"])
            )

        st.caption(
            f"Input totals before Set E exclusion: courses={result.get('input_total_courses')}, credits={result.get('input_total_credits')}"
        )

        breakdown = result.get("set_breakdown", {}) or {}
        cat_rows = [
            {
                "Category": "Compulsory",
                "Satisfied": "Yes" if (breakdown.get("set_d", {}).get("is_satisfied")) else "No",
                "Taken": breakdown.get("set_d", {}).get("taken_count", 0),
                "Rule check": f"missing {len(breakdown.get('set_d', {}).get('missing_required', []))}",
            },
            {
                "Category": "Elective options",
                "Satisfied": "Yes" if (breakdown.get("set_a", {}).get("is_satisfied", True) and breakdown.get("set_b", {}).get("is_satisfied", True)) else "No",
                "Taken": (
                    breakdown.get("set_a", {}).get("taken_count", 0)
                    + breakdown.get("set_b", {}).get("taken_count", 0)
                    + breakdown.get("set_c", {}).get("taken_count", 0)
                ),
                "Rule check": (
                    f"min elective target {breakdown.get('set_a', {}).get('required_min', 0)}"
                    if breakdown.get("set_a", {}).get("is_configured")
                    else "no minimum target"
                ),
            },
            {
                "Category": "Not counted",
                "Satisfied": "Yes" if (breakdown.get("set_e", {}).get("excluded_count", 0) == 0) else "No",
                "Taken": breakdown.get("set_e", {}).get("excluded_count", 0),
                "Rule check": "excluded from totals",
            },
        ]
        _show_df(cat_rows, use_container_width=True)

        not_selected_rows = _not_selected_requirement_rows(
            criteria,
            pathway,
            course_index,
            program_label=f"{subject} {p_type}",
        )
        if not_selected_rows:
            with st.expander("Requirement courses not selected"):
                _show_df(not_selected_rows, use_container_width=True)

        if result.get("errors"):
            st.error("Requirement violations found")
            for err in result["errors"]:
                st.markdown(f"- {err}")
        else:
            st.success("Pathway satisfies current rules")

        with st.expander("Validation report"):
            st.json(result)
            st.download_button(
                "Download report JSON",
                data=json.dumps(result, indent=2),
                file_name=f"validation_report_{subject}_{p_type}.json".replace(" ", "_"),
                mime="application/json",
                key=f"download_{state_key}",
            )


def _render_quality(courses, programs):
    st.subheader("Data Quality")

    report = cg.build_quality_report(courses, programs)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Duplicate course codes", len(report["duplicate_course_codes"]))
    c2.metric("Missing prereq links", len(report["missing_prereq_links"]))
    c3.metric("Duplicate program entries", len(report["duplicate_program_entries"]))
    c4.metric("Programs w/ unknown rule codes", len(report["unknown_requirement_codes"]))

    if (
        not report["duplicate_course_codes"]
        and not report["missing_prereq_links"]
        and not report["duplicate_program_entries"]
        and not report["unknown_requirement_codes"]
        and not report["missing_semesters"]
        and not report["self_prereq_courses"]
    ):
        st.success("No blocking quality issues found")
    else:
        st.warning("Some quality checks reported issues. Expand sections below.")

    if report["duplicate_course_codes"]:
        with st.expander("Duplicate course codes"):
            st.json(report["duplicate_course_codes"])

    if report["missing_prereq_links"]:
        with st.expander("Missing prerequisite links"):
            st.json(report["missing_prereq_links"])

    if report["duplicate_program_entries"]:
        with st.expander("Duplicate major/minor entries"):
            st.json(report["duplicate_program_entries"])

    if report["unknown_requirement_codes"]:
        with st.expander("Unknown requirement codes"):
            st.json(report["unknown_requirement_codes"])

    if report["missing_semesters"]:
        with st.expander("Courses missing semester tags"):
            st.json(report["missing_semesters"])

    if report["self_prereq_courses"]:
        with st.expander("Self prerequisite courses"):
            st.json(report["self_prereq_courses"])


def _load_data(courses_relative):
    courses = cg.load_courses(courses_relative)
    programs = cg.load_programs()

    if not courses:
        raise ValueError("No courses found in selected course file")

    return courses, programs


def main():
    st.set_page_config(layout="wide", page_title="Curriculum Graph Studio")
    _inject_design()
    _hero()

    courses_relative = Path(sys.argv[1]) if len(sys.argv) > 1 else cg.DEFAULT_COURSES_PATH

    try:
        courses, programs = _load_data(courses_relative)
    except FileNotFoundError as err:
        st.error(f"Missing data file: {err}")
        st.stop()
    except ValueError as err:
        st.error(str(err))
        st.stop()

    try:
        constraints = cg.load_constraints()
    except FileNotFoundError:
        constraints = {"min_degree_credits": 184, "num_semesters": 8}

    course_index = cg.index_courses(courses)
    program_index_raw, duplicate_keys = cg.build_program_index(programs)
    program_index, removed_program_keys = _filter_program_index_for_policy(program_index_raw)

    _render_overview(courses, programs)

    if duplicate_keys:
        duplicate_text = ", ".join([f"{s} {t}" for s, t in duplicate_keys])
        st.warning("Duplicate program entries found; first entry used for each key: " + duplicate_text)

    if removed_program_keys:
        removed_text = ", ".join([f"{subject} {p_type}" for subject, p_type in removed_program_keys])
        st.info(
            "Policy filter active. Showing only allowed IISER options: "
            "Majors in Physics/Chemistry/Biology/Earth and Climate Science and minors in those plus Data Science. "
            "Filtered out: " + removed_text
        )

    tab_catalog, tab_roadmap, tab_planner, tab_simulator, tab_algorithms, tab_rules, tab_validate, tab_quality = st.tabs(
        [
            "Catalog Graph",
            "Major/Minor Roadmap",
            "Student Planner",
            "Combination Simulator",
            "Pathway Algorithms",
            "Rules Explorer",
            "Pathway Validation",
            "Data Quality",
        ]
    )

    with tab_catalog:
        _render_catalog_graph(courses, course_index, program_index, constraints)

    with tab_roadmap:
        _render_program_roadmap(program_index, course_index)

    with tab_planner:
        _render_student_planner(program_index, course_index, constraints)

    with tab_simulator:
        _render_combination_simulator(program_index, course_index, constraints)

    with tab_algorithms:
        _render_pathway_algorithms(program_index, course_index)

    with tab_rules:
        _render_rules(program_index, course_index)

    with tab_validate:
        _render_validation(program_index, course_index)

    with tab_quality:
        _render_quality(courses, programs)


if __name__ == "__main__":
    main()
