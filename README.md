# Curriculum Graph Studio

Curriculum Graph Studio is a student-first curriculum planning dashboard for IISER Pune data.
It combines interactive prerequisite graphs, major/minor pathway logic, semester planning, and report generation.

## Why This Exists

- Help students see prerequisite dependencies clearly.
- Support semester-by-semester planning toward the 184-credit target.
- Compare major/minor pathways with feasibility checks.
- Provide reproducible report artifacts (markdown + plots) for review and handoff.

## Dashboard Highlights

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

## Quick Start (Clone-Safe)

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Run the dashboard.

```bash
python -m streamlit run src/app.py
```

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

## Generate Detailed Report With Plots

Run from repository root:

```bash
python src/generate_dashboard_report.py \
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

1. Syntax check:

```bash
python -m py_compile src/app.py src/graph.py src/validate_major_minor.py src/generate_dashboard_report.py
```

2. Dashboard startup smoke test:

```bash
python -m streamlit run src/app.py --server.headless true --server.port 8522
```

3. Regenerate report before merge (for latest data snapshot).

## Notes

- App entrypoint: `src/app.py`
- Logic layer: `src/graph.py`
- Legacy scripts are preserved in `src/legacy/` and are not required for main dashboard flow.