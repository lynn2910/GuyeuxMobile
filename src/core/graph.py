import math
from typing import Optional, List

import networkx as nx
from models.edges.base_edge import BaseEdge
import matplotlib.pyplot as plt

from models.intersections.base_intersection import BaseIntersection


class RoadGraph:
    """
    Represents the road network as a directed graph.

    This class wraps a NetworkX DiGraph to provide specialized methods for
    building and interacting with a road network, including nodes (intersections),
    edges (roads), and pathfinding.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.intersections = {}

    def add_node(self, node_id: str, x: float, y: float):
        """Adds a node to the graph with specified coordinates."""
        self.graph.add_node(node_id, x=x, y=y)

    def add_edge(self, src: str, dst: str, edge_obj: BaseEdge):
        """Adds a directed edge to the graph, represented by a custom edge object."""
        self.graph.add_edge(src, dst, object=edge_obj)

    def add_edge_back_and_forth(self, a: str, b: str, edge_obj: BaseEdge):
        """Adds edges in both directions between two nodes."""
        self.graph.add_edge(a, b, object=edge_obj)
        self.graph.add_edge(b, a, object=edge_obj)

    def get_edge(self, a: str, b: str) -> BaseEdge:
        """
        Retrieves the custom edge object for a directed edge.

        Raises:
            RuntimeError: If no edge is found between the specified nodes.
        """
        edge_data = self.graph.get_edge_data(a, b)
        if edge_data is None:
            raise RuntimeError(f"No edge found from {a} to {b}")
        return edge_data["object"]

    def get_edges(self):
        """Returns an iterator over all edges in the graph with their data."""
        return self.graph.edges(data=True)

    def get_node(self, node_id: str):
        """Retrieves the data associated with a specific node."""
        return self.graph.nodes[node_id]

    def get_path(self, src: str, dst: str, eval_func) -> List[str]:
        """
        Calculates the shortest path between two nodes using the A* algorithm.

        Args:
            src: The starting node ID.
            dst: The destination node ID.
            eval_func: A function to evaluate the weight of each edge during pathfinding.

        Returns:
            A list of node IDs representing the path.

        Raises:
            RuntimeError: If no path is found.
        """

        def euclidean_heuristic(u, v):
            # Heuristic function for A*: estimates the distance to the target.
            try:
                x1, y1 = self.graph.nodes[u]['x'], self.graph.nodes[u]['y']
                x2, y2 = self.graph.nodes[v]['x'], self.graph.nodes[v]['y']
                return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
            except KeyError:
                return 0

        try:
            return nx.astar_path(
                self.graph,
                src,
                dst,
                heuristic=euclidean_heuristic,
                weight=eval_func
            )
        except nx.NetworkXNoPath:
            raise RuntimeError(f"No path found between '{src}' and '{dst}' using A*")

    def show_map(self, file_name: str):
        """
        Generates and saves a visual representation of the graph to a file.
        """
        pos = {
            node_id: (data['x'], data['y'])
            for node_id, data in self.graph.nodes(data=True)
        }

        plt.figure(figsize=(10, 8))

        nx.draw(
            self.graph,
            pos=pos,
            with_labels=True,
            node_size=700,
            node_color='skyblue',
            font_size=10,
            font_weight='bold',
            arrowsize=20
        )

        plt.title("Map Visualization (Real Coordinates)")
        plt.axis('equal')
        plt.savefig(f"data/results/{file_name}.png")

    def add_intersection(self, intersection: BaseIntersection):
        """Attaches intersection logic to an existing node."""
        if self.graph.has_node(intersection.node_id):
            self.intersections[intersection.node_id] = intersection

    def get_intersection(self, node_id: str) -> Optional[BaseIntersection]:
        """Retrieves the intersection logic object for a given node ID."""
        return self.intersections.get(node_id)

    def get_incoming_nodes(self, node_id: str) -> List[str]:
        """Utility to get all nodes that have an edge leading to this node."""
        return list(self.graph.predecessors(node_id))

    def update_intersections(self):
        """Called by the simulation at each tick to update all intersection states."""
        for intersect in self.intersections.values():
            intersect.update()
