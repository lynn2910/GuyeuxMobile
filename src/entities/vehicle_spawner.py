import random
import uuid
from core.graph import RoadGraph
from entities.vehicle import Vehicle


def dynamic_weight(u, v, data):
    """
    A dynamic weight function for pathfinding that delegates the cost calculation
    to the specific edge model's `evaluate_weight` static method.

    This allows the A* algorithm to correctly calculate path costs regardless of
    whether the edge is a CellularEdge, FluidEdge, or any other BaseEdge implementation.

    Args:
        u: The source node of the edge.
        v: The destination node of the edge.
        data: The edge's data dictionary from the graph.

    Returns:
        The calculated weight (cost) for traversing the edge.
    """
    edge = data.get('object')
    if edge:
        # type(edge) gets the class (e.g., FluidEdge or CellularEdge)
        # and we then call its static method evaluate_weight.
        return type(edge).evaluate_weight(u, v, data)
    return 1  # Fallback cost if the edge object is missing.


class VehicleSpawner:
    """
    Manages the creation of new vehicles at a specific node in the graph.

    A spawner attempts to create and insert a new vehicle into the simulation
    at each time step, based on a given probability (spawn_ratio).
    """

    def __init__(self, spawn_ratio: float, node: str):
        """
        Initializes the vehicle spawner.

        Args:
            spawn_ratio (float): The probability (0.0 to 1.0) of spawning a
                                 vehicle at each simulation tick.
            node (str): The ID of the node where vehicles will be spawned.
        """
        self.spawn_ratio = spawn_ratio
        self.node = node

    def update(self, graph: RoadGraph) -> Vehicle | None:
        """
        Attempts to spawn a new vehicle.

        If a random check passes, it chooses a random destination, calculates a path,
        creates a new vehicle, and tries to place it on the first edge of that path.

        Args:
            graph (RoadGraph): The main road graph.

        Returns:
            A new Vehicle object if successfully spawned and placed, otherwise None.
        """
        if random.random() > self.spawn_ratio:
            return None

        # Select a random destination from all other nodes in the graph.
        all_nodes = list(graph.graph.nodes)
        possible_destinations = [n for n in all_nodes if n != self.node]
        if not possible_destinations:
            return None
        destination = random.choice(possible_destinations)

        # Find a path to the destination using the dynamic weight function.
        try:
            path = graph.get_path(self.node, destination, dynamic_weight)
        except RuntimeError:
            # No path could be found between the spawner and the destination.
            return None

        if not path or len(path) < 2:
            return None

        # Create the vehicle.
        veh_id = f"auto_{str(uuid.uuid4())[:5]}"
        # The vehicle's path excludes the starting node.
        vehicle = Vehicle(vehicle_id=veh_id, path=path[1:])

        # Try to place the vehicle on the first edge of its path.
        next_node = path[1]
        start_edge = graph.get_edge(self.node, next_node)

        if start_edge:
            # The insert_vehicle method returns False if the edge is full.
            if start_edge.insert_vehicle(vehicle):
                return vehicle

        return None
