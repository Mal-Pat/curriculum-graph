import sys
import json
import streamlit as st
import graph_analysis
from yfiles_graphs_for_streamlit import StreamlitGraphWidget, Node, Edge, Layout

def make_graph(courses):
    courses = courses.get("all_courses", [])
    nodes, edges = [], []

    # Create unique Group Nodes for each Semester
    all_sems = sorted(list(set(min(c['semesters']) for c in courses)))
    for sem in all_sems:
        nodes.append(Node(
            id=f"group_sem_{sem}",
            properties={
                "label": f"Semester {sem}",
                "isGroup": True
            }
        ))

    # Add Course Nodes and assign them to their Semester Group
    for course in courses:
        code = course['course_code']
        min_sem = min(course['semesters'])
        
        # Color coding for "kind"
        color_map = {
            "normal": "#17a2b8", 
            "lab": "#28a745", 
            "semester_project": "#ffc107"
        }
        node_color = color_map.get(course['kind'], "#6c757d")

        nodes.append(Node(
            id=code,
            properties={
                "label": f"{code}\n{course['course_name']}",
                "parent_id": f"group_sem_{min_sem}",
                "color": node_color,
                "credits": course['credits'],
                "subject": course['subject']
            }
        ))

    # Add Prerequisite Edges
    for course in courses:
        target = course['course_code']
        for prereq in course['prerequisites']:
            edges.append(Edge(
                id=f"{prereq}-{target}",
                start=prereq,
                end=target
            ))

    st.title("Interactive Course Graph")
    st.info("Explore all IISER-P courses")

    # Initialize and Render the Widget
    widget = StreamlitGraphWidget(
        nodes=nodes,
        edges=edges,
        node_label_mapping="label",
        node_color_mapping="color",
        node_parent_mapping="parent_id"
    )
    
    # Call show() with the hierarchic layout constant
    widget.show(graph_layout=Layout.HIERARCHIC)

if __name__ == "__main__":

    if len(sys.argv) > 1:
        data_path = sys.argv[1]
    else:
        data_path = "IISER-P/all_courses.json"

    st.set_page_config(layout="wide", page_title="Course Graph")
    
    with open(f"data/{data_path}", "r") as file:
        courses = json.load(file)

    make_graph(courses)