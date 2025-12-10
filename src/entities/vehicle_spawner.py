import random
import uuid
from core.graph import RoadGraph
from entities.vehicle import Vehicle
from models.cellular import CellularEdge


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

        print("Spawning a vehicle...")

        all_nodes = list(graph.graph.nodes)

        possible_destinations = [n for n in all_nodes if n != self.node]

        print(possible_destinations)

        if not possible_destinations:
            print("no possible_destinations")
            return None

        destination = random.choice(possible_destinations)
        print(destination)

        path = graph.get_path(self.node, destination, CellularEdge.evaluate_weight)
        print(path)

        if not path or len(path) < 2:
            print("no path")
            return None

        veh_id = f"auto_{str(uuid.uuid4())[:5]}"
        print(veh_id)

        vehicle = Vehicle(vehicle_id=veh_id, path=path[1:])

        next_node = path[1]
        start_edge = graph.get_edge(self.node, next_node)
        print(next_node)
        print(start_edge)

        if start_edge:
            start_edge.insert_vehicle(vehicle)
            print(f"Spawn: {veh_id} from {self.node} to {destination}")
            return vehicle

        return None
