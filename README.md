# Curriculum Graph Studio

Curriculum Graph Studio is a student-first curriculum planning dashboard for IISER Pune data.
It combines interactive prerequisite graphs, major/minor pathway logic, semester planning, and report generation.

## What This Project Solves

- Explore how courses connect through prerequisites.
- Understand year-to-year and semester-to-semester transitions.
- Plan toward the 184-credit target with constraints.
- Evaluate major/minor combinations with feasibility checks.
- Generate a detailed report with plots for review and handoff.

## Current Dashboard Highlights

- Student mode by default (cleaner tabs and graph presets).
- Advanced analysis tabs available via toggle.
- Policy-filtered program options:
    - Majors: Physics, Chemistry, Biology, Earth and Climate Science
    - Minors: Physics, Chemistry, Biology, Earth and Climate Science, Data Science
- Catalog graph with year/semester structure and prerequisite flow options.
- Major/Minor roadmap graph with requirement-aware coloring.
- Student planner with credit tracking, requirement progress, and constrained term planning.
- Combination simulator across major-minor pairs.
- Validation, rules explorer, and data quality diagnostics.

## Project Layout

```text
curriculum-graph/
├── README.md
├── START_HERE.md
├── requirements.txt
├── data/
│   ├── courses_schema.json
│   ├── major_minor_schema.json
│   └── IISER-P/
│       ├── all_courses.json
│       ├── major_minor_requirements.json
│       └── college_constraints.json
├── docs/
│   ├── note.txt
│   └── reports/
│       └── latest/
│           ├── dashboard_report.md
│           ├── report_summary.json
│           └── plots/
└── src/
        ├── app.py
        ├── graph.py
        ├── validate_major_minor.py
        ├── generate_dashboard_report.py
        └── legacy/
```

## Quick Start

1. Create and activate a Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the dashboard:

```bash
streamlit run src/app.py
```

4. Open the local URL shown in terminal (usually http://localhost:8501).

## Generate Detailed Report With Plots

Run:

```bash
/Users/ayush/miniconda3/envs/graph_env/bin/python src/generate_dashboard_report.py \
    --courses data/IISER-P/all_courses.json \
    --programs data/IISER-P/major_minor_requirements.json \
    --constraints data/IISER-P/college_constraints.json \
    --out-dir docs/reports/latest
```

Artifacts produced:

- `docs/reports/latest/dashboard_report.md`
- `docs/reports/latest/report_summary.json`
- `docs/reports/latest/plots/*.png`

## Merge Readiness Checklist

- Syntax check:

```bash
/Users/ayush/miniconda3/envs/graph_env/bin/python -m py_compile src/app.py src/graph.py src/validate_major_minor.py src/generate_dashboard_report.py
```

- Dashboard startup smoke test:

```bash
PYTHONPATH=src /Users/ayush/miniconda3/envs/graph_env/bin/streamlit run src/app.py --server.headless true --server.port 8522
```

- Regenerate report before merge (for latest data snapshot).

## Notes

- The app entrypoint is `src/app.py`.
- `src/graph.py` is the logic layer for data/graph/planning utilities.
- Legacy scripts are preserved in `src/legacy/` and are not required for main dashboard flow.