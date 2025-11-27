# run_cellular.py
import os
from os import path

from core.graph import RoadGraph
from core.simulation import Simulation
from entities.vehicle import Vehicle
from models.cellular import CellularEdge


# ---------------- SETUP ---------------- #

def init_required_files_and_folders():
    target_path = path.join("data", "results")
    os.makedirs(target_path, exist_ok=True)


# ---------------- CONFIG ---------------- #

def build_sample_city() -> RoadGraph:
    road = RoadGraph()

    # --- NODES --- #
    road.add_node("A", 0, 0)
    road.add_node("B", 1, 0)
    road.add_node("C", 1, 1)

    # --- EDGES --- #
    road.add_edge("A", "B", CellularEdge(distance=20, vmax=5, prob_slow=0.1))
    road.add_edge("B", "C", CellularEdge(distance=30, vmax=11, prob_slow=0.1))

    return road


# ---------------- MAIN ---------------- #

def run_cellular():
    init_required_files_and_folders()

    road = build_sample_city()
    path_func = CellularEdge.evaluate_weight

    vehicle_path = road.get_path("A", "C", path_func)
    print("Chemin trouvé:", vehicle_path)

    simulation = Simulation(road, 1)

    # Vehicle 1: starts at edge A->B
    vehicle1 = Vehicle(vehicle_id=1, path=vehicle_path[1:])
    start_edge1 = road.get_edge("A", "B")
    simulation.add_vehicle(vehicle1, start_edge1)

    # Vehicle 2: starts at edge A->B (a bit delayed)
    vehicle2 = Vehicle(vehicle_id=2, path=vehicle_path[1:])
    start_edge2 = road.get_edge("A", "B")
    simulation.add_vehicle(vehicle2, start_edge2)

    # Run simulation for a limited number of ticks
    simulation.running = True
    max_ticks = 20

    while simulation.running and simulation.t < max_ticks:
        simulation.tick()

        # Stop if all vehicles have exited
        if len(simulation.vehicles) == 0:
            print("\nAll vehicles have completed their journey!")
            simulation.running = False


if __name__ == "__main__":
    run_cellular()
