"""Generate clean PNG visualizations for major/minor requirements.

Usage examples:
  python src/visualize_major_minor_requirements.py --out-dir outputs
  python src/visualize_major_minor_requirements.py --subject Biology --program Major --out-dir outputs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _entry_key(entry: dict) -> tuple[str, str]:
    md = entry.get("program_metadata", {})
    return md.get("subject", ""), md.get("major_or_minor", "")


def _entry_map(requirements: list[dict]) -> dict[tuple[str, str], dict]:
    return {_entry_key(e): e for e in requirements}


def _countable_courses(entry: dict) -> set[str]:
    sets = entry.get("requirements_by_set", {})
    pool = set()
    for key in ["set_a", "set_b", "set_c"]:
        block = sets.get(key) or {}
        pool.update(block.get("available_courses", []))
    block_d = sets.get("set_d") or {}
    pool.update(block_d.get("compulsory_courses", []))
    return pool


def _subject_order(requirements: list[dict]) -> list[str]:
    subjects = sorted({e.get("program_metadata", {}).get("subject", "") for e in requirements})
    return [s for s in subjects if s]


def plot_overview(requirements: list[dict], out_path: Path) -> None:
    by_key = _entry_map(requirements)
    subjects = _subject_order(requirements)

    major_vals = []
    minor_vals = []
    major_colors = []
    minor_colors = []

    for s in subjects:
        major = by_key.get((s, "Major"), {})
        minor = by_key.get((s, "Minor"), {})

        major_min = major.get("overall_requirements", {}).get("minimum_total_courses")
        minor_min = minor.get("overall_requirements", {}).get("minimum_total_courses")

        major_vals.append(major_min or 0)
        minor_vals.append(minor_min or 0)

        major_colors.append("#2f7ed8" if major.get("is_offered", False) else "#cccccc")
        minor_colors.append("#4caf50" if minor.get("is_offered", False) else "#cccccc")

    y = list(range(len(subjects)))
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh([i + 0.2 for i in y], major_vals, height=0.35, color=major_colors, label="Major min courses")
    ax.barh([i - 0.2 for i in y], minor_vals, height=0.35, color=minor_colors, label="Minor min courses")

    for i, s in enumerate(subjects):
        major = by_key.get((s, "Major"), {})
        minor = by_key.get((s, "Minor"), {})
        if not major.get("is_offered", False):
            ax.text(0.2, i + 0.2, "Not offered", va="center", fontsize=8, color="#666")
        if not minor.get("is_offered", False):
            ax.text(0.2, i - 0.2, "Not offered", va="center", fontsize=8, color="#666")

    ax.set_yticks(y)
    ax.set_yticklabels(subjects)
    ax.set_xlabel("Minimum counted courses")
    ax.set_title("Major/Minor Requirement Overview by Subject")
    ax.legend(loc="lower right")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_subject_program(
    requirements: list[dict],
    all_courses: list[dict],
    subject: str,
    program: str,
    out_path: Path,
) -> None:
    by_key = _entry_map(requirements)
    key = (subject, program)
    if key not in by_key:
        raise ValueError(f"No entry found for {subject} {program}")

    entry = by_key[key]
    code_to_course = {c.get("course_code"): c for c in all_courses if c.get("course_code")}

    countable = sorted(_countable_courses(entry))
    semester_counts: dict[int, int] = {}
    kind_counts: dict[str, int] = {"normal": 0, "lab": 0, "semester_project": 0, "other": 0}

    for code in countable:
        course = code_to_course.get(code)
        if not course:
            continue
        sems = sorted(course.get("semesters", []))
        if sems:
            semester_counts[sems[0]] = semester_counts.get(sems[0], 0) + 1
        kind = course.get("kind", "normal")
        if kind in kind_counts:
            kind_counts[kind] += 1
        else:
            kind_counts["other"] += 1

    set_a = entry.get("requirements_by_set", {}).get("set_a") or {}
    set_b = entry.get("requirements_by_set", {}).get("set_b") or {}
    set_d = entry.get("requirements_by_set", {}).get("set_d") or {}

    fig, axs = plt.subplots(2, 2, figsize=(14, 9))

    # Panel 1: Summary block
    axs[0, 0].axis("off")
    summary_lines = [
        f"Subject: {subject}",
        f"Program: {program}",
        f"Offered: {entry.get('is_offered')}",
        f"Complete: {entry.get('is_complete')}",
        f"Prerequisites policy: {entry.get('prerequisites_policy', 'strict')}",
        f"Min courses: {entry.get('overall_requirements', {}).get('minimum_total_courses')}",
        f"Min credits: {entry.get('overall_requirements', {}).get('minimum_total_credits')}",
        f"Countable course pool: {len(countable)}",
        f"Set D mandatory count: {len(set_d.get('compulsory_courses', []))}",
    ]
    if set_a:
        summary_lines.append(f"Set A min from set: {set_a.get('minimum_required_from_set')}")
    if set_b:
        summary_lines.append(f"Set B max from set: {set_b.get('maximum_allowed_from_set')}")

    axs[0, 0].text(0.02, 0.98, "\n".join(summary_lines), va="top", fontsize=10)

    # Panel 2: Semester distribution
    sems = sorted(semester_counts)
    counts = [semester_counts[s] for s in sems]
    axs[0, 1].bar(sems, counts, color="#2f7ed8")
    axs[0, 1].set_title("Countable Courses by First Offered Semester")
    axs[0, 1].set_xlabel("Semester")
    axs[0, 1].set_ylabel("Course count")
    axs[0, 1].grid(axis="y", linestyle="--", alpha=0.3)

    # Panel 3: Kind distribution
    labels = [k for k, v in kind_counts.items() if v > 0]
    values = [kind_counts[k] for k in labels]
    colors = {
        "normal": "#4c78a8",
        "lab": "#f58518",
        "semester_project": "#54a24b",
        "other": "#9d755d",
    }
    axs[1, 0].bar(labels, values, color=[colors[l] for l in labels])
    axs[1, 0].set_title("Countable Courses by Kind")
    axs[1, 0].set_ylabel("Course count")
    axs[1, 0].grid(axis="y", linestyle="--", alpha=0.3)

    # Panel 4: Notes
    axs[1, 1].axis("off")
    notes = entry.get("notes", [])
    note_text = "Notes:\n- " + "\n- ".join(notes) if notes else "Notes: None"
    axs[1, 1].text(0.02, 0.98, note_text, va="top", fontsize=10)

    fig.suptitle(f"Major/Minor Rule Snapshot: {subject} {program}", fontsize=14, weight="bold")
    plt.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize major/minor requirements")
    parser.add_argument("--requirements", default="data/IISER-P/major_minor_requirements.json")
    parser.add_argument("--courses", default="data/IISER-P/all_courses.json")
    parser.add_argument("--out-dir", default="outputs")
    parser.add_argument("--subject", help="Optional subject for detail chart")
    parser.add_argument("--program", choices=["Major", "Minor"], help="Required when --subject is set")
    args = parser.parse_args()

    requirements = _load_json(Path(args.requirements))
    all_courses = _load_json(Path(args.courses)).get("all_courses", [])

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    overview_path = out_dir / "major_minor_overview.png"
    plot_overview(requirements, overview_path)
    print(f"wrote {overview_path}")

    if args.subject and args.program:
        detail_path = out_dir / f"{args.subject.replace(' ', '_').lower()}_{args.program.lower()}_requirements.png"
        plot_subject_program(requirements, all_courses, args.subject, args.program, detail_path)
        print(f"wrote {detail_path}")


if __name__ == "__main__":
    main()
