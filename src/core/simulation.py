# src/core/simulation.py
from time import sleep, time
import config
from cli import debug_log


class Simulation:
    def __init__(self, graph, tps: float, visualizer=None):
        self.graph = graph
        self.vehicles = []
        self.spawners = []

        self.tps = tps
        self.tick_duration = 1.0 / tps

        self.t = 0
        self.running = False

        self.since_last_update = 0

        self.visualizer = visualizer

    def add_vehicle(self, vehicle, start_edge):
        """
        Add a vehicle to the simulation, inserting it to the desired edge.
        """
        vehicle.current_edge = start_edge
        start_edge.insert_vehicle(vehicle)
        self.vehicles.append(vehicle)

    def add_spawner(self, spawner):
        """Register a new spawner in the simulation"""
        self.spawners.append(spawner)

    def remove_vehicle_safely(self, vehicle):
        """Helper to safely remove a vehicle without crashing if it's already gone."""
        try:
            self.vehicles.remove(vehicle)
        except ValueError:
            pass  # Vehicle was already removed, likely due to a multi-hop update

    def tick(self):
        """
        The main loop of the simulation.
        """
        start_time = time()

        if self.since_last_update >= self.tick_duration:
            self.t += 1
            # print(f"------ Tick {self.t} ------")

            self.internal_step()

            self.since_last_update -= self.tick_duration

        if self.visualizer:
            self.visualizer.update(self.t)
            if not self.visualizer.handle_events():
                self.running = False
                return

        elapsed = time() - start_time

        self.since_last_update += elapsed

    def internal_step(self):
        """
        Do all the work for one single update
        """
        # 1. Spawners
        for spawner in self.spawners:
            new_vehicle = spawner.update(self.graph)
            if new_vehicle:
                self.vehicles.append(new_vehicle)
                if config.DEBUG:
                    print(f"Spawned vehicle {new_vehicle.id} at {spawner.node}")

        # 2. Edges & Vehicles move
        # On récupère toutes les edges. Note : l'ordre d'itération peut influencer les "doubles sauts"
        for src, dist, data in self.graph.get_edges():
            edge = data['object']
            exiting_vehicles = edge.update()

            if config.DEBUG and exiting_vehicles:
                print(f"\nEdge from {src} to {dist} :")
                edge.draw_console()
                print(f"{len(exiting_vehicles)} exiting vehicles")

            for vehicle in exiting_vehicles:
                vehicle.pop_next_target()
                next_node = vehicle.next_target()

                if next_node is None:
                    # Le véhicule est arrivé à destination
                    self.remove_vehicle_safely(vehicle)
                else:
                    current_node = dist
                    try:
                        next_edge = self.graph.get_edge(current_node, next_node)
                        vehicle.current_edge = next_edge

                        # Tentative d'insertion sur la route suivante
                        inserted = next_edge.insert_vehicle(vehicle)

                        # Note: Si inserted est False (route pleine), le véhicule est dans 
                        # la file d'attente (Cellular) ou rejeté (Fluid).
                        # Pour l'instant on le garde dans self.vehicles.

                    except RuntimeError:
                        if config.DEBUG:
                            print(f"Vehicle {vehicle.id} vanished: no edge {current_node}->{next_node}")
                        self.remove_vehicle_safely(vehicle)
