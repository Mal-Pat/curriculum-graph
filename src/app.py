import json
import sys
from pathlib import Path

import graph as cg
import streamlit as st
from validate_major_minor import validate_major_minor_pathway
from yfiles_graphs_for_streamlit import Layout, StreamlitGraphWidget


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

    role_color = {
        "major": "#0077b6",
        "minor": "#2a9d8f",
        "both": "#e76f51",
        "support": "#6c757d",
    }

    for year in range(y_min, y_max + 1):
        nodes.append(
            cg.Node(
                id=f"group_combined_year_{year}",
                properties={"label": f"Year {year}", "isGroup": True},
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
        nodes.append(
            cg.Node(
                id=code,
                properties={
                    "label": label,
                    "parent_id": f"group_combined_year_{year}",
                    "color": role_color[role],
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

    return nodes, edges, graph


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


def _render_catalog_graph(courses, course_index, program_index):
    st.subheader("Course Catalog Graph")

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
        query = st.text_input("Search by course code or name")

        col1, col2, col3 = st.columns(3)
        include_prereqs = col1.checkbox("Include prerequisite chain", value=True)
        hide_isolated = col2.checkbox("Hide isolated nodes", value=False)
        focus_program = col3.checkbox("Focus on one program rule list", value=False)

        focus_codes = None
        if focus_program and program_index:
            subject, p_type = _subject_type_selector(program_index, "catalog_focus")
            if subject and p_type:
                criteria = program_index[(subject, p_type)]
                focus_codes = cg.collect_requirement_codes(criteria)

    filtered = cg.filter_courses(courses, selected_subjects, selected_kinds, sem_range, query)

    if focus_codes is not None:
        filtered = [c for c in filtered if c.get("course_code") in focus_codes]

    if include_prereqs and filtered:
        filtered = cg.expand_with_prereqs(filtered, course_index)

    if hide_isolated and filtered:
        filtered = cg.remove_isolated_courses(filtered)

    if not filtered:
        st.warning("No courses match current filters")
        return

    nodes, edges = cg.make_semester_graph_elements(filtered)

    st.write(
        {
            "visible_courses": len([n for n in nodes if not n.id.startswith("group_sem_")]),
            "visible_semester_groups": len([n for n in nodes if n.id.startswith("group_sem_")]),
            "visible_edges": len(edges),
        }
    )

    st.caption("Node color by kind: normal=#1f7a8c, lab=#2a9d8f, semester_project=#e9c46a")

    widget = StreamlitGraphWidget(
        nodes=nodes,
        edges=edges,
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id",
        directed_mapping="directed",
    )
    widget.show(graph_layout=Layout.HIERARCHIC, key="catalog_graph_widget")


def _render_program_roadmap(program_index, course_index):
    st.subheader("Major/Minor Roadmap Graph")
    st.caption("Pick a program to see Year 1 to Year 4 pathway with prerequisites linked.")

    if not program_index:
        st.info("No major/minor program rules loaded")
        return

    subject, p_type = _subject_type_selector(program_index, "roadmap")
    if not subject or not p_type:
        st.info("No program selection available")
        return

    criteria = program_index[(subject, p_type)]

    set_cols = st.columns(5)
    selected_sets = []
    for idx, set_name in enumerate(["set_a", "set_b", "set_c", "set_d", "set_e"]):
        if set_cols[idx].checkbox(set_name.upper(), value=True, key=f"roadmap_{set_name}"):
            selected_sets.append(set_name)

    col1, col2, col3 = st.columns(3)
    include_prereq_support = col1.checkbox(
        "Add support prerequisites",
        value=True,
        help="Also show prerequisite courses that are not explicitly listed in rule sets.",
    )
    year_range = col2.slider("Year range", min_value=1, max_value=4, value=(1, 4))
    compact_mode = col3.checkbox("Compact layout", value=False)

    roadmap = cg.make_program_roadmap_elements(
        criteria,
        course_index,
        include_prereq_support=include_prereq_support,
        selected_sets=selected_sets,
        year_range=year_range,
    )

    nodes = roadmap["nodes"]
    edges = roadmap["edges"]

    if not nodes or len([n for n in nodes if not n.id.startswith("group_year_")]) == 0:
        st.warning("No roadmap courses available for this selection")
        return

    st.write(
        {
            "program_courses_found": len(roadmap["base_codes_present"]),
            "program_courses_missing": len(roadmap["base_codes_missing"]),
            "visible_courses": len([n for n in nodes if not n.id.startswith("group_year_")]),
            "visible_edges": len(edges),
        }
    )

    if roadmap["base_codes_missing"]:
        st.warning("Some rule-list courses are missing from catalog data")
        st.dataframe(
            {"missing_course_codes": roadmap["base_codes_missing"]},
            use_container_width=True,
        )

    st.caption(
        "Set colors: SET_D=#d1495b, SET_A=#0077b6, SET_B=#f4a261, SET_C=#2a9d8f, SET_E=#8d99ae, PREREQ=#6c757d"
    )

    widget = StreamlitGraphWidget(
        nodes=nodes,
        edges=edges,
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id",
        directed_mapping="directed",
    )
    widget.show(
        graph_layout=Layout.ORTHOGONAL if compact_mode else Layout.HIERARCHIC,
        key="roadmap_graph_widget",
    )


def _render_student_planner(program_index, course_index, constraints):
    st.subheader("Student Planner")
    st.caption("Track progress to 184 credits by Semester 8 while balancing major and minor requirements.")

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

    default_seed = ", ".join(
        [
            cg.suggest_pathway(major_criteria, limit=12),
            cg.suggest_pathway(minor_criteria, limit=8),
        ]
    )
    state_key = "planner_completed_courses"
    if state_key not in st.session_state:
        st.session_state[state_key] = default_seed

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
                st.write(f"- {err}")
        else:
            st.write("No major requirement violations for current input")

    with st.expander("Minor requirement gaps"):
        if minor_result.get("errors"):
            for err in minor_result["errors"]:
                st.write(f"- {err}")
        else:
            st.write("No minor requirement violations for current input")

    combined_nodes, combined_edges, combined_graph = _major_minor_combined_elements(
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
                    "semester": sem,
                    "courses": ", ".join(codes),
                    "course_count": len(codes),
                    "semester_credits": sem_credits,
                    "projected_total_credits": cumulative,
                }
            )
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No schedule generated. Try increasing max courses/credits per term.")

    if plan_payload.get("blocked_details"):
        with st.expander("Blocked courses in planner"):
            st.dataframe(plan_payload["blocked_details"], use_container_width=True)

    st.markdown("#### Combined Major-Minor Dependency Graph")
    st.caption("Color legend: MAJOR=blue, MINOR=teal, BOTH=orange, SUPPORT PREREQ=gray")
    planner_widget = StreamlitGraphWidget(
        nodes=combined_nodes,
        edges=combined_edges,
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id",
        directed_mapping="directed",
    )
    planner_widget.show(graph_layout=Layout.HIERARCHIC, key="student_planner_graph_widget")


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

    set_cols = st.columns(5)
    selected_sets = []
    for idx, set_name in enumerate(["set_a", "set_b", "set_c", "set_d", "set_e"]):
        if set_cols[idx].checkbox(set_name.upper(), value=True, key=f"algo_{set_name}"):
            selected_sets.append(set_name)

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
        st.dataframe(cycle_rows, use_container_width=True)

    st.markdown("#### Topological Order")
    topo = analysis["topological_order"]
    if topo:
        st.dataframe(
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
        st.dataframe(plan_rows, use_container_width=True)
    else:
        st.info("No courses could be scheduled with current constraints.")

    if plan_payload.get("blocked_details"):
        with st.expander("Blocked courses details"):
            st.dataframe(plan_payload["blocked_details"], use_container_width=True)

    if unreachable:
        with st.expander("Unreachable nodes details"):
            st.dataframe({"course_code": unreachable}, use_container_width=True)

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
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No representative paths available for current selection.")

    st.markdown("#### Bottleneck Courses")
    bottlenecks = analysis["bottlenecks"]
    if bottlenecks:
        st.dataframe(bottlenecks, use_container_width=True)
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

    widget = StreamlitGraphWidget(
        nodes=roadmap["nodes"],
        edges=roadmap["edges"],
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id",
        directed_mapping="directed",
    )
    widget.show(graph_layout=Layout.HIERARCHIC, key="algorithms_graph_widget")


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
    by_set = cg.requirement_codes_by_set(criteria)

    c1, c2 = st.columns(2)
    c1.metric("Minimum total courses", overall.get("minimum_total_courses"))
    c2.metric("Minimum total credits", overall.get("minimum_total_credits"))

    st.markdown("#### Rule footprint")
    st.dataframe(
        [{"Set": k.upper(), "Courses listed": len(v)} for k, v in by_set.items()],
        use_container_width=True,
    )

    unknown_codes = sorted([code for code in cg.collect_requirement_codes(criteria) if code not in course_index])
    if unknown_codes:
        st.warning("Unknown codes in requirement list: " + ", ".join(unknown_codes))

    for set_name in ["set_a", "set_b", "set_c", "set_d", "set_e"]:
        st.markdown(f"#### {set_name.upper()}")
        st.dataframe(_course_rows(by_set.get(set_name, []), course_index), use_container_width=True)

    with st.expander("Raw criteria JSON"):
        st.json(criteria)


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
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()
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

    st.write({"parsed_courses": len(pathway), "unknown_codes": len(unknown_codes)})
    if rows:
        st.dataframe(rows, use_container_width=True)

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

        st.caption(
            f"Input totals before Set E exclusion: courses={result.get('input_total_courses')}, credits={result.get('input_total_credits')}"
        )

        breakdown = result.get("set_breakdown", {})
        if breakdown:
            st.dataframe(
                [
                    {
                        "Set": s.upper(),
                        "Satisfied": d.get("is_satisfied"),
                        "Taken": d.get("taken_count", d.get("excluded_count", 0)),
                        "Rule": (
                            f"min {d.get('required_min')}" if s == "set_a" else
                            f"max {d.get('allowed_max')}" if s == "set_b" else
                            f"required {d.get('required_count')}" if s == "set_d" else
                            "informational"
                        ),
                    }
                    for s, d in breakdown.items()
                ],
                use_container_width=True,
            )

        if result.get("errors"):
            st.error("Requirement violations found")
            for err in result["errors"]:
                st.write(f"- {err}")
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
    program_index, duplicate_keys = cg.build_program_index(programs)

    _render_overview(courses, programs)

    if duplicate_keys:
        duplicate_text = ", ".join([f"{s} {t}" for s, t in duplicate_keys])
        st.warning("Duplicate program entries found; first entry used for each key: " + duplicate_text)

    tab_catalog, tab_roadmap, tab_planner, tab_algorithms, tab_rules, tab_validate, tab_quality = st.tabs(
        [
            "Catalog Graph",
            "Major/Minor Roadmap",
            "Student Planner",
            "Pathway Algorithms",
            "Rules Explorer",
            "Pathway Validation",
            "Data Quality",
        ]
    )

    with tab_catalog:
        _render_catalog_graph(courses, course_index, program_index)

    with tab_roadmap:
        _render_program_roadmap(program_index, course_index)

    with tab_planner:
        _render_student_planner(program_index, course_index, constraints)

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
