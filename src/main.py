"""
Main entry point for the traffic simulation application.

This script handles command-line argument parsing, map file loading,
and the initialization of the main simulation loop.
"""
import os
from os import path

from cli import parse_arguments, debug_log
from core.fs.parser import import_map
from core.simulation import Simulation
from ui.visualizer import Visualizer


def init_required_files_and_folders():
    """
    Ensures that necessary directories for storing results exist.
    """
    target_path = path.join("data", "results")
    os.makedirs(target_path, exist_ok=True)


def run_simulation_from_file(file_path: str, tps: float, show_viz: bool):
    """
    Loads a map file and runs the traffic simulation.

    This function orchestrates the entire process:
    1. Initializes required folders.
    2. Parses the specified .map file to build the graph, vehicles, and spawners.
    3. Optionally initializes the Pygame visualizer.
    4. Creates and runs the main Simulation object.

    Args:
        file_path (str): The path to the .map file.
        tps (float): The number of simulation ticks to run per second.
        show_viz (bool): If True, the graphical visualizer will be enabled.
    """
    init_required_files_and_folders()

    print(f"Loading configuration from '{file_path}'...\n")
    graph, vehicles, spawners = import_map(file_path)

    print(f"Graph loaded: {len(graph.graph.nodes)} nodes, {len(graph.graph.edges)} edges")
    print(f"Initial vehicles: {len(vehicles)}")
    print(f"Spawners: {len(spawners)}")

    # Generate a static image of the graph layout.
    print("\nGenerating graph map image...")
    file_name = path.basename(file_path).split('.')[0]
    graph.show_map(file_name)
    print(f"Map image saved to data/results/{file_name}.png")

    # Initialize the visualizer if requested.
    viz = None
    if show_viz:
        print("\nInitializing visualizer...")
        viz = Visualizer(graph)

    # Create and configure the main simulation object.
    simulation = Simulation(graph, tps, visualizer=viz)
    simulation.spawners = spawners

    print("\n----- Initial Vehicles -----")
    for vehicle, start_edge in vehicles:
        simulation.add_vehicle(vehicle, start_edge)
        debug_log(f"Vehicle {vehicle.id} added with path: {vehicle.path}")

    # --- Main Simulation Loop ---
    print(f"\nLaunching simulation at {tps} TPS... (Press Ctrl+C to stop)")
    simulation.running = True
    try:
        while simulation.running:
            simulation.tick()
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    finally:
        if viz:
            viz.close()
        print(f"\nSimulation finished after {simulation.t} ticks.")


if __name__ == "__main__":
    # Parse command-line arguments.
    args = parse_arguments()

    debug_log(f"Map file: {args.map}")
    debug_log(f"TPS: {args.tps}")
    debug_log(f"Visualizer enabled: {args.visualizer}")

    # Start the simulation with the parsed arguments.
    run_simulation_from_file(
        file_path=args.map,
        tps=args.tps,
        show_viz=args.visualizer
    )
