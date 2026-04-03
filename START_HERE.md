## Start Here (Current Dashboard)

This project runs through `src/app.py`.

### 1) Install dependencies

Create and activate a virtual environment first (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2) Run dashboard

```bash
python -m streamlit run src/app.py
```

### 3) Generate detailed report + plots

```bash
python src/generate_dashboard_report.py \
  --courses data/IISER-P/all_courses.json \
  --programs data/IISER-P/major_minor_requirements.json \
  --constraints data/IISER-P/college_constraints.json \
  --out-dir docs/reports/latest
```

Generated artifacts:

- `docs/reports/latest/dashboard_report.md`
- `docs/reports/latest/report_summary.json`
- `docs/reports/latest/plots/*.png`

### 4) Merge-ready sanity checks

```bash
python -m py_compile src/app.py src/graph.py src/validate_major_minor.py src/generate_dashboard_report.py
```

```bash
python -m streamlit run src/app.py --server.headless true --server.port 8522
```
