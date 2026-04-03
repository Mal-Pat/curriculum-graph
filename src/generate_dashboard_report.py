"""Generate a detailed curriculum dashboard report with plots.

This script creates a merge-ready report artifact that summarizes:
- curriculum inventory and coverage,
- prerequisite network health,
- major/minor program profile,
- quality checks,
- visual plots for quick inspection.

Example:
  /Users/ayush/miniconda3/envs/graph_env/bin/python src/generate_dashboard_report.py \
    --courses data/IISER-P/all_courses.json \
    --programs data/IISER-P/major_minor_requirements.json \
    --constraints data/IISER-P/college_constraints.json \
    --out-dir docs/reports/latest
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

import graph as cg


def _resolve_input_path(raw_path: str) -> Path:
    """Resolve an input path from either repo root or data-relative form."""

    path = Path(raw_path)
    if path.exists():
        return path

    alt = Path("data") / raw_path
    if alt.exists():
        return alt

    raise FileNotFoundError(f"Input file not found: {raw_path}")


def _load_courses(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("all_courses", [])


def _load_programs(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return cg.normalize_programs(payload)


def _load_constraints(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _first_semester(course: dict) -> int | None:
    semesters = course.get("semesters") or []
    if not semesters:
        return None
    return min(int(sem) for sem in semesters)


def _year_from_semester(sem: int) -> int:
    return ((int(sem) - 1) // 2) + 1


def _save_plot(fig, out_path: Path) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path.name


def plot_courses_by_first_semester(courses: list[dict], plot_dir: Path) -> str:
    counts = Counter()
    for course in courses:
        sem = _first_semester(course)
        if sem is not None:
            counts[sem] += 1

    semesters = sorted(counts)
    values = [counts[s] for s in semesters]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(semesters, values, color="#1d4ed8")
    ax.set_title("Courses by First Offered Semester")
    ax.set_xlabel("Semester")
    ax.set_ylabel("Number of Courses")
    ax.grid(axis="y", linestyle="--", alpha=0.25)

    return _save_plot(fig, plot_dir / "courses_by_first_semester.png")


def plot_credits_by_first_semester(courses: list[dict], plot_dir: Path) -> str:
    sem_credits = Counter()
    for course in courses:
        sem = _first_semester(course)
        if sem is None:
            continue
        sem_credits[sem] += int(course.get("credits", 0) or 0)

    semesters = sorted(sem_credits)
    values = [sem_credits[s] for s in semesters]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(semesters, values, color="#0f766e")
    ax.set_title("Credits by First Offered Semester")
    ax.set_xlabel("Semester")
    ax.set_ylabel("Total Credits")
    ax.grid(axis="y", linestyle="--", alpha=0.25)

    return _save_plot(fig, plot_dir / "credits_by_first_semester.png")


def plot_courses_by_year(courses: list[dict], plot_dir: Path) -> str:
    year_counts = Counter()
    for course in courses:
        sem = _first_semester(course)
        if sem is None:
            continue
        year_counts[_year_from_semester(sem)] += 1

    years = sorted(year_counts)
    values = [year_counts[y] for y in years]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(years, values, color="#c2410c")
    ax.set_title("Courses by Academic Year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Courses")
    ax.grid(axis="y", linestyle="--", alpha=0.25)

    return _save_plot(fig, plot_dir / "courses_by_year.png")


def plot_subject_distribution(courses: list[dict], plot_dir: Path, top_n: int) -> str:
    subject_counts = Counter((course.get("subject") or "Unknown") for course in courses)
    ordered = sorted(subject_counts.items(), key=lambda item: item[1], reverse=True)[:top_n]

    subjects = [subject for subject, _ in ordered]
    values = [count for _, count in ordered]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(subjects, values, color="#7c3aed")
    ax.set_title(f"Top {top_n} Subjects by Course Count")
    ax.set_xlabel("Subject")
    ax.set_ylabel("Number of Courses")
    ax.tick_params(axis="x", rotation=32)
    ax.grid(axis="y", linestyle="--", alpha=0.25)

    return _save_plot(fig, plot_dir / "subject_distribution_top.png")


def plot_kind_distribution(courses: list[dict], plot_dir: Path) -> str:
    kind_counts = Counter((course.get("kind") or "unknown") for course in courses)
    labels = list(kind_counts.keys())
    values = [kind_counts[label] for label in labels]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title("Course Kind Distribution")

    return _save_plot(fig, plot_dir / "kind_distribution.png")


def plot_prerequisite_count_distribution(courses: list[dict], plot_dir: Path) -> str:
    counts = Counter(len(course.get("prerequisites") or []) for course in courses)
    x_vals = sorted(counts)
    y_vals = [counts[x] for x in x_vals]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x_vals, y_vals, color="#1e293b")
    ax.set_title("Prerequisite Count Distribution")
    ax.set_xlabel("Number of Prerequisites")
    ax.set_ylabel("Number of Courses")
    ax.grid(axis="y", linestyle="--", alpha=0.25)

    return _save_plot(fig, plot_dir / "prerequisite_count_distribution.png")


def plot_subject_semester_heatmap(courses: list[dict], plot_dir: Path, top_subjects: int) -> str:
    subject_counts = Counter((course.get("subject") or "Unknown") for course in courses)
    top_subject_list = [subject for subject, _ in subject_counts.most_common(top_subjects)]

    sem_values = sorted(
        {
            int(sem)
            for course in courses
            for sem in (course.get("semesters") or [])
            if sem is not None
        }
    )

    if not sem_values:
        sem_values = [1]

    sem_index = {sem: idx for idx, sem in enumerate(sem_values)}
    subject_index = {subject: idx for idx, subject in enumerate(top_subject_list)}

    matrix = [[0 for _ in sem_values] for _ in top_subject_list]

    for course in courses:
        subject = course.get("subject") or "Unknown"
        if subject not in subject_index:
            continue
        row = subject_index[subject]

        for sem in (course.get("semesters") or []):
            sem = int(sem)
            if sem in sem_index:
                col = sem_index[sem]
                matrix[row][col] += 1

    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(matrix, aspect="auto", cmap="YlGnBu")
    ax.set_title("Subject vs Semester Offering Heatmap")
    ax.set_xlabel("Semester")
    ax.set_ylabel("Subject")
    ax.set_xticks(list(range(len(sem_values))))
    ax.set_xticklabels(sem_values)
    ax.set_yticks(list(range(len(top_subject_list))))
    ax.set_yticklabels(top_subject_list)
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)

    return _save_plot(fig, plot_dir / "subject_semester_heatmap.png")


def _markdown_table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "_No rows available._\n"

    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = [
        "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, divider] + body) + "\n"


def _program_profile(programs: list[dict]) -> list[dict]:
    profile = Counter()
    for criteria in programs:
        subject, p_type = cg.program_key(criteria)
        label = f"{subject} {p_type}"
        profile[label] += 1

    rows = []
    for label, count in sorted(profile.items()):
        rows.append({"Program": label, "Entries": count})
    return rows


def _top_bottlenecks(courses: list[dict], top_n: int) -> list[dict]:
    course_index = cg.index_courses(courses)
    graph = cg.build_dependency_digraph(course_index, set(course_index.keys()))
    rows = cg.bottleneck_table(graph, top_n=top_n)

    for row in rows:
        code = row.get("course_code")
        course = course_index.get(code, {})
        row["course_name"] = course.get("course_name", "")

    return rows


def _build_report_markdown(
    generated_at: str,
    courses: list[dict],
    programs: list[dict],
    constraints: dict,
    plot_files: list[str],
    stats: dict,
    quality: dict,
    bottlenecks: list[dict],
    program_rows: list[dict],
) -> str:
    total_courses = len(courses)
    total_programs = len(programs)
    semesters = sorted(
        {
            int(sem)
            for course in courses
            for sem in (course.get("semesters") or [])
            if sem is not None
        }
    )

    sem_range_text = f"S{min(semesters)}-S{max(semesters)}" if semesters else "Unavailable"
    degree_target = int((constraints or {}).get("min_degree_credits", 184) or 184)

    top_subject_rows = [
        {"Subject": subject, "Courses": count}
        for subject, count in Counter((course.get("subject") or "Unknown") for course in courses).most_common(12)
    ]

    unknown_req_total = sum(
        len(items)
        for per_program in quality.get("unknown_requirement_codes", {}).values()
        for items in per_program.values()
    )

    lines = [
        "# Curriculum Dashboard Report",
        "",
        f"Generated: {generated_at}",
        "",
        "## Executive Summary",
        f"- Total courses: {total_courses}",
        f"- Program criteria entries: {total_programs}",
        f"- Subjects covered: {stats.get('subjects', 0)}",
        f"- Prerequisite edges in catalog graph: {stats.get('prereq_edges', 0)}",
        f"- Average credits per course: {stats.get('avg_credits', 0)}",
        f"- Semester coverage: {sem_range_text}",
        f"- Degree target from constraints: {degree_target}",
        "",
        "## Data Health Snapshot",
        f"- Duplicate course codes: {len(quality.get('duplicate_course_codes', {}))}",
        f"- Missing prerequisite links: {len(quality.get('missing_prereq_links', {}))}",
        f"- Duplicate program entries: {len(quality.get('duplicate_program_entries', {}))}",
        f"- Programs with unknown requirement codes: {len(quality.get('unknown_requirement_codes', {}))}",
        f"- Total unknown requirement code hits: {unknown_req_total}",
        f"- Courses missing semester tags: {len(quality.get('missing_semesters', []))}",
        f"- Self prerequisite courses: {len(quality.get('self_prereq_courses', []))}",
        "",
        "## Subject Coverage",
        _markdown_table(top_subject_rows, ["Subject", "Courses"]),
        "## Program Entries",
        _markdown_table(program_rows, ["Program", "Entries"]),
        "## Top Bottleneck Courses",
        _markdown_table(
            bottlenecks,
            [
                "course_code",
                "course_name",
                "in_degree",
                "direct_dependents",
                "all_downstream",
                "betweenness",
            ],
        ),
        "## Plot Gallery",
    ]

    for plot_file in plot_files:
        title = plot_file.replace("_", " ").replace(".png", "").title()
        lines.append(f"### {title}")
        lines.append(f"![{title}](plots/{plot_file})")
        lines.append("")

    lines.extend(
        [
            "## Merge Readiness Notes",
            "- Student mode and advanced mode tabs are available in the Streamlit dashboard.",
            "- Program options are policy-filtered for the requested IISER major/minor combinations.",
            "- Graph labels, legends, and semester transition summaries are now student-facing and cleaner.",
            "- Run the smoke-check command before merging: `python -m py_compile src/app.py src/graph.py`.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a detailed curriculum dashboard report with plots")
    parser.add_argument("--courses", default="data/IISER-P/all_courses.json", help="Path to all_courses JSON")
    parser.add_argument(
        "--programs",
        default="data/IISER-P/major_minor_requirements.json",
        help="Path to major/minor requirement JSON",
    )
    parser.add_argument(
        "--constraints",
        default="data/IISER-P/college_constraints.json",
        help="Path to college constraints JSON",
    )
    parser.add_argument("--out-dir", default="docs/reports/latest", help="Output directory for report artifacts")
    parser.add_argument("--top-subjects", type=int, default=12, help="Top N subjects shown in charts")
    parser.add_argument("--top-bottlenecks", type=int, default=12, help="Top N bottlenecks in report table")
    args = parser.parse_args()

    courses_path = _resolve_input_path(args.courses)
    programs_path = _resolve_input_path(args.programs)
    constraints_path = _resolve_input_path(args.constraints)

    out_dir = Path(args.out_dir)
    plot_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    courses = _load_courses(courses_path)
    programs = _load_programs(programs_path)
    constraints = _load_constraints(constraints_path)

    stats = cg.build_course_stats(courses, programs)
    quality = cg.build_quality_report(courses, programs)
    bottlenecks = _top_bottlenecks(courses, top_n=args.top_bottlenecks)
    program_rows = _program_profile(programs)

    plot_files = [
        plot_courses_by_first_semester(courses, plot_dir),
        plot_credits_by_first_semester(courses, plot_dir),
        plot_courses_by_year(courses, plot_dir),
        plot_subject_distribution(courses, plot_dir, args.top_subjects),
        plot_kind_distribution(courses, plot_dir),
        plot_prerequisite_count_distribution(courses, plot_dir),
        plot_subject_semester_heatmap(courses, plot_dir, top_subjects=min(args.top_subjects, 10)),
    ]

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_text = _build_report_markdown(
        generated_at=generated_at,
        courses=courses,
        programs=programs,
        constraints=constraints,
        plot_files=plot_files,
        stats=stats,
        quality=quality,
        bottlenecks=bottlenecks,
        program_rows=program_rows,
    )

    report_path = out_dir / "dashboard_report.md"
    report_path.write_text(report_text, encoding="utf-8")

    summary_path = out_dir / "report_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "courses": len(courses),
                "program_entries": len(programs),
                "stats": stats,
                "quality_counts": {
                    "duplicate_course_codes": len(quality.get("duplicate_course_codes", {})),
                    "missing_prereq_links": len(quality.get("missing_prereq_links", {})),
                    "duplicate_program_entries": len(quality.get("duplicate_program_entries", {})),
                    "programs_with_unknown_codes": len(quality.get("unknown_requirement_codes", {})),
                    "missing_semesters": len(quality.get("missing_semesters", [])),
                    "self_prereq_courses": len(quality.get("self_prereq_courses", [])),
                },
                "plots": plot_files,
                "report_markdown": str(report_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Report written: {report_path}")
    print(f"Summary written: {summary_path}")
    print(f"Plots written: {plot_dir}")
    for plot_file in plot_files:
        print(f"- {plot_dir / plot_file}")


if __name__ == "__main__":
    main()
