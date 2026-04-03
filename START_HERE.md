## Start Here (Clean Main Baseline)

Your repository is now reset to `origin/main` and ready to use.

### 1) Backup of your previous work

Your pre-reset code snapshot is saved here:

`/Users/ayush/Desktop/curriculum-graph_old_code_20260403_194941`

This backup is outside git and safe to inspect anytime.

### 2) Generate quick plots

Run:

```bash
/Users/ayush/miniconda3/envs/graph_env/bin/python src/generate_course_plots.py \
  --courses data/IISER-P/all_courses.json \
  --out-dir outputs/plots
```

This creates:

- `outputs/plots/courses_per_semester.png`
- `outputs/plots/courses_per_year.png`
- `outputs/plots/subject_distribution.png`
- `outputs/plots/kind_distribution.png`
- `outputs/plots/prereq_count_distribution.png`

### 3) Run the app from main

```bash
streamlit run src/graph.py
```

### 4) Optional: compare with your old work

Open this folder to copy ideas/code selectively:

`/Users/ayush/Desktop/curriculum-graph_old_code_20260403_194941`
