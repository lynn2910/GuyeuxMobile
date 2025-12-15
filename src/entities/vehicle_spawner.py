import random
import uuid
from core.graph import RoadGraph
from entities.vehicle import Vehicle


def dynamic_weight(u, v, data):
    """
    Fonction adaptatrice qui délègue le calcul du poids
    à la classe spécifique de l'arête (FluidEdge ou CellularEdge).
    """
    edge = data.get('object')
    if edge:
        # type(edge) renvoie la classe (FluidEdge ou CellularEdge)
        # On appelle ensuite sa méthode statique evaluate_weight
        return type(edge).evaluate_weight(u, v, data)
    return 1  # Fallback si pas d'objet


class VehicleSpawner:
    def __init__(self, spawn_ratio: float, node: str):
        """
        Initiate a spawner
        :param spawn_ratio: The ratio at which cars spawn
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

        # print("Spawning a vehicle...")

        all_nodes = list(graph.graph.nodes)
        possible_destinations = [n for n in all_nodes if n != self.node]

        if not possible_destinations:
            return None

        destination = random.choice(possible_destinations)

        # --- CORRECTION ICI ---
        # On utilise dynamic_weight au lieu de CellularEdge.evaluate_weight
        try:
            path = graph.get_path(self.node, destination, dynamic_weight)
        except RuntimeError:
            # Si aucun chemin n'est trouvé
            return None

        if not path or len(path) < 2:
            return None

        veh_id = f"auto_{str(uuid.uuid4())[:5]}"

        # Création du véhicule (chemin complet sans le noeud de départ)
        vehicle = Vehicle(vehicle_id=veh_id, path=path[1:])

        next_node = path[1]
        start_edge = graph.get_edge(self.node, next_node)

        if start_edge:
            # L'insertion renvoie True si réussie, False si route pleine
            if start_edge.insert_vehicle(vehicle):
                # print(f"Spawn: {veh_id} from {self.node} to {destination}")
                return vehicle

        return None
