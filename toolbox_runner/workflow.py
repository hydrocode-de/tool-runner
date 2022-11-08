"""
"""
from typing import List, Union
from collections import defaultdict
import networkx as nx

from toolbox_runner.tool import Tool

class Workflow:
    def __init__(self):
        # finished steps
        self.steps= defaultdict(lambda: None)
        self.tools = dict()
        self.run_options = defaultdict(lambda: dict())

        # create a Directed Graph
        self.G = nx.DiGraph()

        # add the root node, that starts computations
        self.G.add_node('root')

    def add_tool(self, tool: Tool, requires: List[str] = [], **kwargs):
        """Add a tool to the graph"""
        # get tool name
        tname = tool.name

        # check if we have the tool already
        suffix = ""
        while f"{tname}{suffix}" in self.G.nodes:
            suffix = str(int(suffix) - 1) if suffix != "" else "-1"
        if suffix != "":
            tname = f"{tname}{suffix}"

        # add the node and run options
        self.G.add_node(tname, requires=requires)
        self.tools[tname] = tool
        self.run_options[tname] = kwargs

        return tname

    def generate_graph(self):
        """
        To generate a dependency graph, go for each node and check the requirements.
        Then add directed edges to model dependencies.
        The last step is to bind all nodes without predecessors to the 'root' node
        """
        # first build the edges
        for node in self.G:
            # check if this node has requirements
            if 'requires' in self.G.nodes[node]:
                # check the requirements
                requires = []
                for r in self.G.nodes[node]['requires']:
                    tool = r.split('.').pop()
                    if tool not in requires:
                        requires.append(tool)
                
                # build the edges
                for tname in requires:
                    self.G.add_edge(node, tool)
            else:
                # add edge from root to n
                self.G.add_edge('root', node)

    @property
    def orphans(self) -> List[str]:
        """Returns a list of orphan tool processing names"""
        return [k for k,v in self.G.degree() if v == 0]

    @property
    def connected(self) -> bool:
        """Returns True, if there are no orphan tools"""
        return len(self.orphans) == 0

    @property
    def cycles(self) -> List[List[str]]:
        return nx.simple_cycles(self.G)

    @property
    def linear(self) -> bool:
        """Returns True, if there are no cycles"""
        return len(self.cycles) == 0

    @property
    def valid(self) -> bool:
        """
        Returns True if there is more than one Node, all nodes are 
        connected and no cycles are build into the graph
        """
        return len(self.G.nodes) > 1 and self.linear and self.connected
    
    
        