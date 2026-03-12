import json
import re
import networkx as nx

# -----------------------
# LOAD DATA
# -----------------------

with open("data/processed/courses.json") as f:
    courses = json.load(f)

G = nx.DiGraph()

# -----------------------
# ADD NODES
# -----------------------

for c in courses:

    code = c.get("course_code")

    if not code:
        continue

    dept = code[:2]

    G.add_node(
        code,
        department=dept,
        title=c.get("title"),
        credits=c.get("credits"),
        semester=c.get("semester")
    )


# -----------------------
# ADD EDGES
# -----------------------

for c in courses:

    course_code = c.get("course_code")
    prereq_text = c.get("prerequisites")

    if not prereq_text:
        continue

    prereqs = re.findall(r"[A-Z]{2}\d{4}", prereq_text)

    for p in prereqs:

        if p in G.nodes:
            G.add_edge(p, course_code)


print("\nTotal Courses:", G.number_of_nodes())
print("Total Prerequisite Links:", G.number_of_edges())


# -----------------------
# PRINT DEPARTMENT GRAPHS
# -----------------------

departments = sorted(set(nx.get_node_attributes(G,"department").values()))

for dept in departments:

    print("\n============================")
    print("Department:", dept)
    print("============================")

    dept_nodes = [n for n in G.nodes if G.nodes[n]["department"] == dept]

    for node in dept_nodes:

        children = list(G.successors(node))

        if children:
            for c in children:
                print(f"{node}  --->  {c}")
        else:
            print(f"{node}")