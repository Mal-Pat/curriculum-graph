# Course Data Extraction

This script extracts structured course information from **IISER Pune course content PDFs** and converts it into a machine-readable **JSON dataset**.

The extracted dataset will later be used to build a **Curriculum Dependency Graph** for exploring course prerequisites and degree pathways.

---

## Input

The script reads all PDF files from:

```
data/IISER_P_official_data/2026 January Semester/Course Contents/
```

Each PDF corresponds to **one course**.

---

## Output

The script generates:

```
data/processed/courses.json
```

This file contains structured information for all courses.

---

## Extracted Fields

Each course in the JSON file contains the following fields:

| Field            | Description                                |
| ---------------- | ------------------------------------------ |
| `course_code`    | Unique course identifier                   |
| `title`          | Course title                               |
| `semester`       | Semester in which the course is offered    |
| `nature`         | Course type (Lecture, Lab, Tutorial, etc.) |
| `credits`        | Number of credits                          |
| `prerequisites`  | Required background or courses             |
| `objectives`     | Course learning objectives                 |
| `course_content` | Topics covered in the course               |
| `evaluation`     | Assessment scheme                          |
| `readings`       | Suggested reading materials                |
| `file`           | Source PDF file                            |

---

## Example Output

```json
{
  "course_code": "MT3214",
  "title": "Complex Analysis",
  "semester": 6,
  "nature": "LE - Lecture",
  "credits": 4,
  "prerequisites": "Real Analysis I",
  "objectives": "This course provides an introduction to complex analysis...",
  "course_content": "Topics include holomorphic functions, Cauchy's theorem...",
  "evaluation": "End-sem 35%, Mid-sem 35%, Quiz/Assignment 30%",
  "readings": "S Kumaresan, A Pathway to Complex Analysis...",
  "file": "c40MT3214.pdf"
}
```

---

## Dependencies

Install required libraries:

```
pip install pymupdf
```

---

## Running the Script

```
python src/extract_courses.py
```

The script will process all PDFs and save the extracted dataset.

---

## Purpose

The extracted dataset will be used to:

* build a **course prerequisite graph**
* analyse **curriculum dependencies**
* explore **valid degree pathways**
