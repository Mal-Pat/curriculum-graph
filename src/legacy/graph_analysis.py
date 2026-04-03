import networkx as nx

# To detect_cycles 
def detect_cycles(courses):
    G = nx.DiGraph()

    for course in courses:
        code = course["course_code"]
        for prereq in course["prerequisites"]:
            G.add_edge(prereq, code)

    try:
        cycle = nx.find_cycle(G, orientation="original")
        return cycle
    except:
        return None