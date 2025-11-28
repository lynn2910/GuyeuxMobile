import math
import networkx as nx
from models.base import BaseEdge
import matplotlib.pyplot as plt


class RoadGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_node(self, node_id: str, x: float, y: float):
        self.graph.add_node(node_id, x=x, y=y)

    def add_edge(self, src: str, dst: str, edge_obj: BaseEdge):
        self.graph.add_edge(src, dst, object=edge_obj)

    def add_edge_back_and_forth(self, a: str, b: str, edge_obj: BaseEdge):
        self.graph.add_edge(a, b, object=edge_obj)
        self.graph.add_edge(b, a, object=edge_obj)

    def get_edge(self, a: str, b: str):
        edge_data = self.graph.get_edge_data(a, b)
        if edge_data is None:
            raise RuntimeError(f"No edge found from {a} to {b}")
        return edge_data["object"]

    def get_edges(self):
        return self.graph.edges(data=True)

    def get_node(self, node_id: str):
        return self.graph.nodes[node_id]

    def get_path(self, src: str, dst: str, eval_func):

        def euclidean_heuristic(u, v):
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
            arrows=True,
            arrowsize=20
        )

        plt.title("Visualisation de la carte (Coordonnées réelles)")
        plt.axis('equal')
        plt.savefig(f"data/results/{file_name}.png")
