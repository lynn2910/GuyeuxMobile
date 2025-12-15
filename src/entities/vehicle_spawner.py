import random
import uuid

from core.graph import RoadGraph
from entities.vehicle import Vehicle
from models.cellular import CellularEdge
from cli import debug_log


class VehicleSpawner:
    def __init__(self, spawn_ratio: float, node: str):
        """
        Initiate a spawner
        :param spawn_ratio: The ratio at which cars spawn ; 1 is VERY BIG (100% chance per tick), and 0 is no-spawning
        :param node: The node identifier at which the spawner is located
        """
        self.spawn_ratio = spawn_ratio
        self.node = node

    def update(self, graph: RoadGraph):
        """
        Attempt to spawn a vehicle based on the spawn ratio.
        """
        if random.random() > self.spawn_ratio:
            return None

        debug_log("Spawning a vehicle...")

        all_nodes = list(graph.graph.nodes)

        possible_destinations = [n for n in all_nodes if n != self.node]

        debug_log(possible_destinations)

        if not possible_destinations:
            debug_log("no possible_destinations")
            return None

        destination = random.choice(possible_destinations)
        debug_log(destination)

        path = graph.get_path(self.node, destination, CellularEdge.evaluate_weight)
        debug_log(path)

        if not path or len(path) < 2:
            debug_log("no path")
            return None

        veh_id = f"auto_{str(uuid.uuid4())[:5]}"
        debug_log(veh_id)

        vehicle = Vehicle(vehicle_id=veh_id, path=path[1:])

        next_node = path[1]
        start_edge = graph.get_edge(self.node, next_node)

        if start_edge:
            start_edge.insert_vehicle(vehicle)
            debug_log(f"Spawn: {veh_id} from {self.node} to {destination}")
            return vehicle

        return None
