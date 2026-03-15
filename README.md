# Curriculum Graph

A college curriculum graph visualizer - allows users to explore valid pathways to complete a major or minor

## How to Start

Create a Python virtual environment (using `uv` or `venv` module).

Clone this repository and navigate to the root of the repo.

After activating your virtual environment, run one of the two commands depending on your Python environment:

```bash
pip install -r requirements.txt # for a venv module env
uv pip install -r requirements.txt # for a uv venv
```

The data for all courses should be added as a Json file following the Json Schema given at `data/courses_schema.json` inside the `data` directory.

Run:

```bash
streamlit run src/graph.py <relative-data-path>
```

where the `<relative-data-path>` is the path of the Json file (which contains all the courses) relative to `data/`.

You can now open the Streamlit app in your browser at `http://localhost:8501` or the local url displayed in the terminal.