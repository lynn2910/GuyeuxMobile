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
        vehicle.current_edge = start_edge
        start_edge.insert_vehicle(vehicle)
        self.vehicles.append(vehicle)

    def add_spawner(self, spawner):
        self.spawners.append(spawner)

    def remove_vehicle_safely(self, vehicle):
        try:
            self.vehicles.remove(vehicle)
        except ValueError:
            pass

    def tick(self):
        start_time = time()

        if self.since_last_update >= self.tick_duration:
            self.t += 1
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
        # 0. Mise à jour des feux
        self.graph.update_intersections()

        # 1. Spawners
        for spawner in self.spawners:
            new_vehicle = spawner.update(self.graph)
            if new_vehicle:
                self.vehicles.append(new_vehicle)
                if config.DEBUG:
                    print(f"Spawned vehicle {new_vehicle.id} at {spawner.node}")

        # 2. Edges & Vehicles move
        # Attention : dst (destination), pas dist (distance)
        for src, dst, data in self.graph.get_edges():
            edge = data['object']

            # Gestion Intersection
            can_pass = True
            intersection = self.graph.get_intersection(dst)
            if intersection:
                can_pass = intersection.can_pass(src)

            # Update Edge
            try:
                exiting_vehicles = edge.update(allow_exit=can_pass)
            except TypeError:
                exiting_vehicles = edge.update()  # Fallback pour FluidEdge pas encore mis à jour

            # Gestion des véhicules sortants
            for vehicle in exiting_vehicles:
                vehicle.pop_next_target()
                next_node = vehicle.next_target()

                if next_node is None:
                    self.remove_vehicle_safely(vehicle)
                else:
                    # CORRECTION ICI : 'dst' au lieu de 'dist'
                    current_node = dst
                    try:
                        next_edge = self.graph.get_edge(current_node, next_node)
                        vehicle.current_edge = next_edge

                        inserted = next_edge.insert_vehicle(vehicle)
                        # Si inserted == False, le véhicule est stocké dans la queue interne de l'edge

                    except RuntimeError:
                        if config.DEBUG:
                            print(f"Vehicle {vehicle.id} vanished: no edge {current_node}->{next_node}")
                        self.remove_vehicle_safely(vehicle)
