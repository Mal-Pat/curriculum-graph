"""Course graph utilities.

Builds a graph from a JSON file like `all_courses.json` and visualizes it with:
- Year clusters (Year 1..4)
- Semester nodes inside each year
- Course nodes under their semester
- Prerequisite edges between courses
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx


def load_courses(json_path: str | Path) -> list[dict]:
    """Load `all_courses` list from a curriculum JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("all_courses", [])


def semester_to_year(semester: int) -> int:
    """Map semester number to year number: 1-2 -> 1, 3-4 -> 2, etc."""
    return (semester + 1) // 2


def build_year_semester_graph(courses: list[dict]) -> nx.DiGraph:
    """Create a directed graph clustered by year and semester.

    Node types:
    - year:     `year_1`, `year_2`, ...
    - semester: `sem_1`, `sem_2`, ...
    - course:   `BI1113`, `PH1213`, ...

    Edge types:
    - contains_year: year -> semester
    - contains_sem: semester -> course
    - prerequisite: prereq_course -> course
    """
    g = nx.DiGraph()

    course_codes = {c.get("course_code") for c in courses if c.get("course_code")}

    # Create year/semester/course nodes and containment edges.
    for course in courses:
        code = course.get("course_code")
        if not code:
            continue

        semesters = sorted(course.get("semesters", []))
        if not semesters:
            continue

        primary_sem = semesters[0]
        year = semester_to_year(primary_sem)

        year_id = f"year_{year}"
        sem_id = f"sem_{primary_sem}"

        g.add_node(year_id, node_type="year", label=f"Year {year}", year=year, level=0)
        g.add_node(
            sem_id,
            node_type="semester",
            label=f"Semester {primary_sem}",
            semester=primary_sem,
            year=year,
            level=1,
        )
        g.add_node(
            code,
            node_type="course",
            label=f"{code}\n{course.get('course_name', '')}",
            course_name=course.get("course_name", ""),
            credits=course.get("credits"),
            subject=course.get("subject", ""),
            kind=course.get("kind", "normal"),
            semester=primary_sem,
            year=year,
            level=2,
        )

        g.add_edge(year_id, sem_id, edge_type="contains_year")
        g.add_edge(sem_id, code, edge_type="contains_sem")

    # Add prerequisite edges (only if both courses exist).
    for course in courses:
        code = course.get("course_code")
        if not code:
            continue
        for prereq in course.get("prerequisites", []):
            if prereq in course_codes:
                g.add_edge(prereq, code, edge_type="prerequisite")

    return g


def _build_layout(g: nx.DiGraph) -> dict:
    """Create a stable custom layout with clear year/semester/course bands."""
    pos: dict = {}

    # Top row: years.
    year_nodes = sorted(
        [n for n, d in g.nodes(data=True) if d.get("node_type") == "year"],
        key=lambda n: g.nodes[n].get("year", 0),
    )
    for i, node in enumerate(year_nodes):
        pos[node] = (i * 6.0, 6.0)

    # Middle row: semesters below the year they belong to.
    sem_nodes = sorted(
        [n for n, d in g.nodes(data=True) if d.get("node_type") == "semester"],
        key=lambda n: g.nodes[n].get("semester", 0),
    )
    sem_x = {}
    for node in sem_nodes:
        sem = g.nodes[node]["semester"]
        year = g.nodes[node]["year"]
        year_x = (year - 1) * 6.0
        offset = -1.2 if sem % 2 == 1 else 1.2
        x = year_x + offset
        pos[node] = (x, 3.4)
        sem_x[sem] = x

    # Bottom area: courses grouped by semester, stacked downward.
    semester_to_courses: dict[int, list[str]] = {}
    for node, data in g.nodes(data=True):
        if data.get("node_type") == "course":
            sem = data["semester"]
            semester_to_courses.setdefault(sem, []).append(node)

    for sem, nodes in semester_to_courses.items():
        nodes.sort()
        center_x = sem_x.get(sem, 0.0)
        width = max(1, len(nodes) - 1)
        for idx, node in enumerate(nodes):
            x = center_x + ((idx - width / 2) * 0.42)
            y = 0.8 - (idx % 3) * 0.52
            pos[node] = (x, y)

    return pos


def _draw_year_panel(ax, g: nx.DiGraph, year: int) -> None:
    """Draw one compact panel for a single year (2 semester columns)."""
    year_courses = [
        n
        for n, d in g.nodes(data=True)
        if d.get("node_type") == "course" and d.get("year") == year
    ]
    year_courses.sort()

    sem_left = (year * 2) - 1
    sem_right = year * 2
    left_courses = [c for c in year_courses if g.nodes[c].get("semester") == sem_left]
    right_courses = [c for c in year_courses if g.nodes[c].get("semester") == sem_right]

    color_by_kind = {
        "normal": "#4c78a8",
        "lab": "#f58518",
        "semester_project": "#54a24b",
    }

    pos = {}
    for idx, code in enumerate(left_courses):
        pos[code] = (0.0, -idx)
    for idx, code in enumerate(right_courses):
        pos[code] = (1.0, -idx)

    local_edges = [
        (u, v)
        for u, v, d in g.edges(data=True)
        if d.get("edge_type") == "prerequisite" and u in pos and v in pos
    ]

    for code in left_courses + right_courses:
        kind = g.nodes[code].get("kind", "normal")
        ax.scatter(
            pos[code][0],
            pos[code][1],
            s=260,
            c=color_by_kind.get(kind, "#9d755d"),
            alpha=0.95,
            edgecolors="white",
            linewidths=0.8,
            zorder=3,
        )
        ax.text(
            pos[code][0],
            pos[code][1],
            code,
            ha="center",
            va="center",
            fontsize=7,
            color="white",
            weight="bold",
            zorder=4,
        )

    for u, v in local_edges:
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", lw=0.7, color="#444", alpha=0.6),
            zorder=2,
        )

    ax.set_title(f"Year {year}", fontsize=12, weight="bold")
    ax.text(0.0, 1.02, f"Semester {sem_left}", transform=ax.transAxes, fontsize=9)
    ax.text(0.68, 1.02, f"Semester {sem_right}", transform=ax.transAxes, fontsize=9)
    ax.set_xlim(-0.4, 1.4)
    ax.set_ylim(-max(len(left_courses), len(right_courses), 1) - 0.5, 0.8)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("#f8f9fb")
    for spine in ax.spines.values():
        spine.set_visible(False)


def visualize_year_semester_graph(g: nx.DiGraph, figsize: tuple[int, int] = (16, 11)) -> None:
    """Visualize a compact, readable year-wise semester structure."""
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    axes = axes.flatten()

    for i, year in enumerate([1, 2, 3, 4]):
        _draw_year_panel(axes[i], g, year)

    fig.suptitle("Curriculum Structure (Year Clusters, Semester Wise)", fontsize=15, weight="bold")
    plt.tight_layout()
    plt.show()


def build_and_plot_from_json(json_path: str | Path) -> nx.DiGraph:
    """One-call helper: load data, build graph, and visualize."""
    courses = load_courses(json_path)
    graph = build_year_semester_graph(courses)
    visualize_year_semester_graph(graph)
    return graph


if __name__ == "__main__":
    build_and_plot_from_json("../data/IISER-P/all_courses.json")