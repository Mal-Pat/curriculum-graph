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
        .main .block-container {
            max-width: 1350px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }
        .hero {
            background: linear-gradient(120deg, #0b3c49 0%, #145374 45%, #f4a261 100%);
            border-radius: 18px;
            padding: 1rem 1.2rem;
            color: #f8f9fa;
            box-shadow: 0 10px 24px rgba(20, 83, 116, 0.25);
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 1.9rem;
            letter-spacing: 0.3px;
        }
        .hero p {
            margin: 0.35rem 0 0 0;
            opacity: 0.95;
            font-size: 1rem;
        }
        .metric-card {
            background: #f7fbfc;
            border: 1px solid #d9e8ed;
            border-radius: 14px;
            padding: 0.65rem 0.9rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            font-weight: 600;
            padding-left: 14px;
            padding-right: 14px;
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
          <p>Explore prerequisites, compare major/minor pathways, and validate student plans across Year 1 to Year 4.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    )
    widget.show(graph_layout=Layout.HIERARCHIC)


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
    )
    widget.show(graph_layout=Layout.ORTHOGONAL if compact_mode else Layout.HIERARCHIC)


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

    course_index = cg.index_courses(courses)
    program_index, duplicate_keys = cg.build_program_index(programs)

    _render_overview(courses, programs)

    if duplicate_keys:
        duplicate_text = ", ".join([f"{s} {t}" for s, t in duplicate_keys])
        st.warning("Duplicate program entries found; first entry used for each key: " + duplicate_text)

    tab_catalog, tab_roadmap, tab_rules, tab_validate, tab_quality = st.tabs(
        [
            "Catalog Graph",
            "Major/Minor Roadmap",
            "Rules Explorer",
            "Pathway Validation",
            "Data Quality",
        ]
    )

    with tab_catalog:
        _render_catalog_graph(courses, course_index, program_index)

    with tab_roadmap:
        _render_program_roadmap(program_index, course_index)

    with tab_rules:
        _render_rules(program_index, course_index)

    with tab_validate:
        _render_validation(program_index, course_index)

    with tab_quality:
        _render_quality(courses, programs)


if __name__ == "__main__":
    main()
