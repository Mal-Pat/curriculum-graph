import json
import pandas as pd
import matplotlib.pyplot as plt

DATA_PATH = "data/IISER-P/all_courses.json"
OUTPUT_PATH = "docs/images/subject_semester_distribution.png"

plt.style.use("ggplot")

# ---------- load dataset ----------
with open(DATA_PATH) as f:
    data = json.load(f)

courses = data["all_courses"]

rows = []

for course in courses:
    subject = course["subject"]
    semester = min(course["semesters"])   # canonical semester
    
    rows.append({
        "subject": subject,
        "semester": semester
    })

df = pd.DataFrame(rows)

# ---------- pivot table ----------
pivot = df.pivot_table(
    index="semester",
    columns="subject",
    aggfunc=len,
    fill_value=0
)

pivot = pivot.sort_index()

# ---------- plot ----------
plt.figure(figsize=(12,6))

pivot.plot(kind="bar")

plt.title("Course Distribution by Subject and Semester", fontsize=16)
plt.xlabel("Semester")
plt.ylabel("Number of Courses")

plt.xticks(rotation=0)

plt.legend(
    title="Subject",
    bbox_to_anchor=(1.02,1),
    loc="upper left"
)

plt.tight_layout()

plt.savefig(OUTPUT_PATH, dpi=300)

plt.close()

print("Saved:", OUTPUT_PATH)