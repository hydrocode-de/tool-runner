"""
Asynchronous and concurrent workflows
-------------------------------------


"""
from typing import List, Dict
import os
import tempfile
import shutil
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from concurrent.futures import Future

from toolbox_runner.tool import Tool
from toolbox_runner.step import Step

class Workflow:
    def __init__(self, mode='auto', work_dir: str = None):
        # options
        self.mode = mode

        # finished steps
        self.steps= defaultdict(lambda: None)
        self.tools = dict()
        self.run_options = defaultdict(lambda: dict())
        self._futures: Dict[str, Future] = defaultdict(lambda: None)

        # TODO: make a temporary folder available here
        if work_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory()
            self.work_dir = self._temp_dir.name
        else:
            self._temp_dir = None
            self.work_dir = work_dir

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
        # get all nodes
        nodes = list(self.G.nodes)
        
        # remove all edges
        self.G.remove_edges_from(list(self.G.edges))

        # first build the edges
        for node in nodes:
            if node == 'root':
                continue

            # check if this node has requirements
            if 'requires' in self.G.nodes[node] and len(self.G.nodes[node]['requires']) > 0:
                # check the requirements
                requires = []
                for r in self.G.nodes[node]['requires']:
                    tool = r.split('::')[::-1].pop()
                    if tool not in requires:
                        requires.append(tool)
                
                # build the edges
                for tname in requires:
                    # get the required files
                    reqs = [r.split('::').pop() for r in self.G.nodes[node]['requires'] if r.startswith(tname)]
                    self.G.add_edge(tname, node, requires=reqs)
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
        return list(nx.simple_cycles(self.G))

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
        return len(list(self.G.nodes)) > 1 and self.linear and self.connected

    @property
    def state(self) -> Dict[str, str]:
        """
        Show the state of all tools.
        Current states are: 

        * invalid: The tool is not connected to Workflow
        * pending: The tool is waiting for execution
        * running: The tool is currently running
        * finished: The tool has submitted results to the Workflow
        * cancelled: The tool was cancelled by the user
        * errored: The tool errored
        * undefined: The Future of the tool was created, but it is not running and not finished


        """
        state = dict(
            root='finished'
        )
        # get all nodes
        nodes =list([n for n in self.G.nodes if n != 'root'])
        
        for n in nodes:
            # if step is there, the node finished
            if n in self.steps and n not in self._futures:
                # this checks if the step was already there to prevent the tool 
                # from running again. in this case, no Future was created, but 
                # the tool can still be considered finished.
                # If the future is present, it could also contain an error, then
                # we check the future state, not the Step.
                state[n] = 'finished'
                continue
                
            # get predecessors and successors
            pre = list(self.G.predecessors(n))
            suc = list(self.G.successors(n))

            if len(suc) == 0 and len(pre) == 0:
                state[n] = 'invalid'
                continue
            
            # check if there is an future for this Node
            if n in self._futures:
                # use the future to determine the state
                if self._futures[n].running():
                    state[n] = 'running'
                elif self._futures[n].cancelled():
                    state[n] = 'cancelled'
                elif self._futures[n].exception() is not None:
                    state[n] = 'errored'
                elif self._futures[n].done():
                    state[n] = 'finished'
                else:
                    state[n] = 'undefined'
            else:
                # did not start so far
                state[n] = 'pending'

        return state

    @property
    def running(self):
        return any([f.running() for f in self._futures.values()])
    
    @property
    def errored(self):
        return any([f.exception() is not None for f in self._futures.values()])
    
    @property
    def cancelled(self):
        return any([f.cancelled() for f in self._futures.values()])

    @property
    def done(self):
        return all([n in self.steps for n in self.G.nodes]) and len(self.steps) > 0

    def clear(self):
        """Clear the internal state of steps and remove the FINISHED subscriber."""
        # clear steps and futures
        self.steps = defaultdict(lambda: None)
        self._futures = defaultdict(lambda: None)

        if Tool.FINISHED.has_receivers_for(self.finish_subscription):
            Tool.FINISHED.disconnect(self.finish_subscription)

    def run(self, work_dir: str = None):
        """
        Run the workflow.
        """
        if not self.valid:
            raise RuntimeError("This workflow is not valid.")
        
        # connect to Tool
        if not Tool.FINISHED.has_receivers_for(self.finish_subscription):
            Tool.FINISHED.connect(self.finish_subscription)
        
        # some stats
        print(f"Starting Workflow\nwd: {self.work_dir}")
        print(f"Tools to run: {len(list(self.G.nodes)) - 1}")

        # Start next iteration
        self.next_iteration('root', work_dir=work_dir if work_dir is not None else self.work_dir)
            
    def finish_subscription(self, data: Dict[str, Step]):
        """
        Subscritpion to the FINISH events.
        Before the events can be handled, the Workflow needs to be connected to
        the tools.
        """
        # get the identifier and step
        identifier = list(data.keys())[0]
        step = data[identifier]
        
        print(f"\n{identifier} finished: {str(step)}")
        
        # got a step, add it to the WF
        self.steps[identifier] = step

        # check if the workflow errored or was canceled in the meantime
        if self.cancelled or self.errored:
            print(f"Stopping dispatcher for Workflow.\nCancelled: {self.cancelled}\tErrored: {self.errored}")
            return

        # now dispatch all successors of this step -> this only happens in mode == 'auto'
        if self.mode.lower() == 'auto':
            self.next_iteration(active_node=identifier, work_dir=self.work_dir)

    def _copy_dependencies_from_edge(self, node, path):
        """
        Get all predecessors from the workflow graph. Each of the edges
        is checked for defined dependency files. Then the Step is opened and
        the corresponding dependency is copied to the shared folder in the
        workflow dir. The Tool can consume these shared files and mount them
        into the docker container on run.

        """
        kwargs = dict()
        for pre in self.G.predecessors(node):
            # get the edge
            edge = self.G[pre][node]

            # check requirements from this edge
            if 'requires' in edge:
                # get the step
                step = self.steps[pre]

                for req in edge['requires']:
                    if req in step.inputs:
                        ar_path = f"./in/{req}"
                    elif req in step.outputs:
                        ar_path = f"./out/{req}"
                    else:
                        raise FileNotFoundError(f"The requirement '{req}' was not found in step: {step}")
                    
                    # write this file to the shared steps
                    fpath = f"{path}/{req}"
                    with open(fpath, 'wb') as f:
                        f.write(step.get_file(ar_path))
                    
                    # append the path to the kwargs
                    kwargs[req.split('.')[0]] = fpath
            else:
                # no requirements defined
                continue
        return kwargs

    def next_iteration(self, active_node, work_dir: str):
        # handle working directories
        dep_path = os.path.join(work_dir, 'shared')
        if not os.path.exists(dep_path):
            os.mkdir(dep_path)

        # get a list of all successors for the current activate node
        # this needs to be copied, as the for-loop is changing the graph
        successors = list(self.G.successors(active_node))
        
        # check and dispatch each successor
        for node in successors:
            # check if the step is already there:
            if node in self.steps:
                print(f"Step '{node}' already done. No force policy found")
                continue

            # get the tool and update the identifier
            tool = self.tools[node]
            if node != tool.IDENTIFIER:
                tool.IDENTIFIER = node
            
            # extract the run-options (parameters)
            kwargs = self.run_options[node]
        
            # check if the new node has all requirements
            if all([pre in self.steps or pre == 'root' for pre in self.G.predecessors(node)]):
                print(f"Found all requirements for '{node}'. Collecting dependencies...", end="")

                # get the files
                dep_kwargs = self._copy_dependencies_from_edge(node, dep_path)
                kwargs.update(dep_kwargs)
                print('done.')

                # run 
                print(f"Dispatching '{node}'...")
                # run the tool and save the future
                future = tool.run(result_path=work_dir, run_async=True, **kwargs)
                self._futures[node] = future
            else:
                print(f"'{node}' is lacking requirements. Waiting for other steps to finish.")
                continue

    def _ipython_display_(self):
        """Return as matplotlib graph"""
        # get the nodes
        nodes = list(self.G.nodes)
        
        # hardcode colormapping
        cm = dict(invalid='#f07579', pending='#8aa4ab', running='#416270', finished='#747c24', errored='#ce3536', cancelled='#f3c58f', undefined='#e3ded9')
        # align colors to inidcate the node state
        state = self.state
        node_colors = [cm[state[n]] for n in nodes]
        
        # draw the network
        nx.draw_networkx(self.G, with_labels=True, nodelist=nodes, node_color=node_colors)
        
        # transparent background
        fig = plt.gcf()
        fig.patch.set_alpha(0.0)
        ax = plt.gca()
        ax.patch.set_alpha(0.0)

        # there you go
        return fig
    
    def __del__(self):
        if self._temp_dir is not None:
            try:
                self._temp_dir.cleanup()
            except Exception:
                pass
