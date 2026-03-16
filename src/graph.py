import sys
import json
import re
import networkx as nx
import matplotlib.pyplot as plt

# -----------------------------------------
# Load courses
# -----------------------------------------

with open("data/processed/courses.json", "r") as f:
    courses = json.load(f)

# -----------------------------------------
# Create graph
# -----------------------------------------

G = nx.DiGraph()

# -----------------------------------------
# Add course nodes
# -----------------------------------------

for course in courses:

    code = course.get("course_code")

    G.add_node(
        code,
        title=course.get("title"),
        credits=course.get("credits"),
        semester=course.get("semester")
    )

# -----------------------------------------
# Add prerequisite edges
# -----------------------------------------

for course in courses:

    course_code = course.get("course_code")
    prereq_text = course.get("prerequisites")

    # skip empty prerequisites
    if not prereq_text:
        continue

    # find course codes like MT3214, PH3244
    prereq_codes = re.findall(r"[A-Z]{2}\d{4}", prereq_text)

    for prereq in prereq_codes:
        G.add_edge(prereq, course_code)

# -----------------------------------------
# Print basic graph info
# -----------------------------------------

print("Total courses:", G.number_of_nodes())
print("Total prerequisite links:", G.number_of_edges())

# -----------------------------------------
# Draw graph
# -----------------------------------------

plt.figure(figsize=(14,10))

pos = nx.kamada_kawai_layout(G)

nx.draw(
    G,
    pos,
    with_labels=True,
    node_color="lightblue",
    node_size=2000,
    font_size=8,
    arrows=True
)

plt.title("Curriculum Graph (Courses and Prerequisites)")
plt.show()