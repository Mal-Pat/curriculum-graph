"""
Custom graph-algorithm for curriculam graph's major minor logic

@author: Artamta
"""
import numpy as np 
import pandas as pd 
import networkx as nx
import json
#import matpotlib.pyplot as plt

#loads file

class File:
    def __init__(self, input_file):
        self.input_file = input_file

    def make_list(self):
        i = 0
        with open(self.input_file, 'r') as file:
            self.data = json.load(file)
            data = self.data
            for course in data["all_courses"]:
                code = course["course_code"]
                sub = course["subject"]
                prereqs = course["prerequisites"]
                credit = course["credits"]
                sem =course["semesters"]
                kind =course["kind"]
                ali=course["aliases"]

        
#make-graph
class Graph:

    def init(self):
        self.name = name

    def graph_init(self):
        #graph-init
        G = nx.Graph()
        G.add_nodes_from(["B", "C", "D"]) #

        # 3. Add edges
        # You can add a single edge (adding an edge automatically adds missing nodes):
        G.add_edge("A", "B")
        # Or add multiple edges from a list of tuples:
        edges = [("B", "C"), ("C", "D"), ("D", "A")]
        G.add_edges_from(edges) #

        # 4. Add attributes (optional)
        G.add_edge("A", "B", weight=4) #

#plotting
class Plot:
    def init(self):
        self.name = name

    def plot():

        # 5. Visualize the graph
        nx.draw(G, with_labels=True, node_color='skyblue', node_size=1000, edge_color='black', font_size=12) #
        plt.title("Simple Network Graph using Python")
        plt.show()

def main():
    input_file = "../data/IISER-P/all_courses.json"
    content_ = File(input_file)
    content = content_.make_list()

   # print("here is content \n",content)
if __name__ == "__main__":
    main()