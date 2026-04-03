"""Generate quick static plots from the course catalog JSON.

Usage:
  /Users/ayush/miniconda3/envs/graph_env/bin/python src/generate_course_plots.py \
    --courses data/IISER-P/all_courses.json \
    --out-dir outputs/plots
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


def _load_courses(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("all_courses", [])


def _first_semester(course: dict) -> int | None:
    semesters = course.get("semesters", [])
    if not semesters:
        return None
    return min(semesters)


def plot_courses_per_semester(courses: list[dict], out_dir: Path) -> Path:
    sem_counts = Counter()
    for c in courses:
        sem = _first_semester(c)
        if sem is not None:
            sem_counts[sem] += 1

    semesters = sorted(sem_counts)
    counts = [sem_counts[s] for s in semesters]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(semesters, counts, color="#2f7ed8")
    ax.set_title("Courses by First Offered Semester")
    ax.set_xlabel("Semester")
    ax.set_ylabel("Number of Courses")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_path = out_dir / "courses_per_semester.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def plot_courses_per_year(courses: list[dict], out_dir: Path) -> Path:
    year_counts = Counter()
    for c in courses:
        sem = _first_semester(c)
        if sem is None:
            continue
        year = (sem - 1) // 2 + 1
        year_counts[year] += 1

    years = sorted(year_counts)
    counts = [year_counts[y] for y in years]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(years, counts, color="#54a24b")
    ax.set_title("Courses by Academic Year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Courses")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_path = out_dir / "courses_per_year.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def plot_subject_distribution(courses: list[dict], out_dir: Path, top_n: int) -> Path:
    subject_counts = Counter(c.get("subject", "Unknown") for c in courses)
    ordered = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

    subjects = [s for s, _ in ordered]
    counts = [c for _, c in ordered]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(subjects, counts, color="#f58518")
    ax.set_title(f"Top {top_n} Subjects by Course Count")
    ax.set_xlabel("Subject")
    ax.set_ylabel("Number of Courses")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_path = out_dir / "subject_distribution.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def plot_kind_distribution(courses: list[dict], out_dir: Path) -> Path:
    kind_counts = Counter(c.get("kind", "unknown") for c in courses)
    labels = list(kind_counts.keys())
    values = [kind_counts[k] for k in labels]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title("Course Kind Distribution")
    plt.tight_layout()

    out_path = out_dir / "kind_distribution.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def plot_prereq_count_distribution(courses: list[dict], out_dir: Path) -> Path:
    prereq_count = Counter(len(c.get("prerequisites", [])) for c in courses)
    x_vals = sorted(prereq_count)
    y_vals = [prereq_count[x] for x in x_vals]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x_vals, y_vals, color="#4c78a8")
    ax.set_title("Distribution of Prerequisite Counts per Course")
    ax.set_xlabel("Number of Prerequisites")
    ax.set_ylabel("Number of Courses")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_path = out_dir / "prereq_count_distribution.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate summary plots for course catalog")
    parser.add_argument("--courses", default="data/IISER-P/all_courses.json")
    parser.add_argument("--out-dir", default="outputs/plots")
    parser.add_argument("--top-subjects", type=int, default=12)
    args = parser.parse_args()

    courses_path = Path(args.courses)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    courses = _load_courses(courses_path)

    written = [
        plot_courses_per_semester(courses, out_dir),
        plot_courses_per_year(courses, out_dir),
        plot_subject_distribution(courses, out_dir, args.top_subjects),
        plot_kind_distribution(courses, out_dir),
        plot_prereq_count_distribution(courses, out_dir),
    ]

    print(f"Generated {len(written)} plots in {out_dir}")
    for p in written:
        print(f"- {p}")


if __name__ == "__main__":
    main()
