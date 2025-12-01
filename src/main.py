# run_cellular.py
import os
from os import path

import networkx as nx
import matplotlib.pyplot as plt

from cli import parse_arguments, debug_log
from core.fs.parser import import_map
from core.graph import RoadGraph
from core.simulation import Simulation
from models.cellular import CellularEdge
from ui.visualizer import Visualizer


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


def run_simulation_from_file(file_path: str, tps: float = 0.5, show_viz: bool = False):
    """
    Execute a simulation from a file
    :param show_viz: Whether to show the visualizer
    :param file_path: The path of the file to be simulated
    :param tps: The number of ticks per second
    """
    init_required_files_and_folders()

    print(f"Loading configuration from '{file_path}'...\n")
    graph, vehicles = import_map(file_path)

    print(f"Graph loaded: {len(graph.graph.nodes)} nodes, {len(graph.graph.edges)} edges")
    print(f"Vehicles loaded: {len(vehicles)}")

    print("\n----- Generate graph -----")
    file_name = path.basename(file_path).replace(".smap", "")
    graph.show_map(file_name)

    viz = None
    if show_viz:
        viz = Visualizer(graph, 800, 500)

    simulation = Simulation(graph, tps, visualizer=viz)

    print("\n----- Vehicles -----")
    for vehicle, start_edge in vehicles:
        simulation.add_vehicle(vehicle, start_edge)
        print(f"Vehicle {vehicle.id} added with path: {vehicle.path}")

    print(f"\nLaunching the simulation...\n")
    simulation.running = True

    while simulation.running:
        simulation.tick()

        # if len(simulation.vehicles) == 0:
        #     print("\nAll vehicles finished their walk-out!")
        #     simulation.running = False

    print(f"\nSimulation finished after {simulation.t} ticks")


if __name__ == "__main__":
    args = parse_arguments()

    debug_log(f"Map file: {args.map}")
    debug_log(f"TPS: {args.tps}")

    run_simulation_from_file(
        file_path=args.map,
        tps=args.tps,
        show_viz=args.visualizer
    )
