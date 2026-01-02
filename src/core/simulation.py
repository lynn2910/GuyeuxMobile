from time import time, sleep
from threading import Thread, Lock
import config
from cli import debug_log


class SharedState:
    """Simple wrapper to mimic multiprocessing.Value interface for threads."""
    def __init__(self, value):
        self.value = value


class Simulation:
    """
    Manages the main simulation loop and state.
    THREADING VERSION: Simulation runs in a separate thread (shared memory).
    """

    def __init__(self, graph, tps: float, visualizer=None):
        self.graph = graph
        self.vehicles = []
        self.spawners = []
        self.tps = tps
        self.tick_duration = 1.0 / tps
        self.visualizer = visualizer

        # Threading - Variables partagées
        self.t = SharedState(0)
        self.running = SharedState(False)
        self.simulation_thread = None
        
        # Cache des edges
        self.active_edges_cache = []
        self.all_edges_cache = [
            (u, v, data['object'])
            for u, v, data in self.graph.get_edges()
        ]

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

    def start(self):
        """Démarre le thread de simulation"""
        self.running.value = True

        self.simulation_thread = Thread(
            target=self._simulation_loop,
            daemon=True
        )
        self.simulation_thread.start()
        print(f"   Simulation thread started")

    def stop(self):
        """Arrête le thread de simulation"""
        self.running.value = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=1.0)

    def _simulation_loop(self):
        """
        Boucle de simulation (tourne dans un thread séparé).
        """
        last_time = time()
        cache_update_counter = 0
        
        print(f"   Simulation loop started in thread")

        while self.running.value:
            current_time = time()
            elapsed = current_time - last_time

            if elapsed >= self.tick_duration:
                # Mise à jour du cache tous les 10 ticks
                cache_update_counter += 1
                if cache_update_counter >= 10:
                    self.active_edges_cache = [
                        (src, dst, edge)
                        for src, dst, edge in self.all_edges_cache
                        if (hasattr(edge, 'vehicles') and edge.vehicles) or
                           (hasattr(edge, 'cells') and any(cell is not None for cell in edge.cells))
                    ]
                    cache_update_counter = 0

                self._internal_step(
                    self.active_edges_cache if self.active_edges_cache else self.all_edges_cache
                )

                self.t.value += 1
                last_time = current_time
                sleep(0.0001)
            else:
                sleep_time = self.tick_duration - elapsed
                if sleep_time > 0:
                    sleep(sleep_time * 0.5)

    def _internal_step(self, edges_to_update):
        # 1. Update traffic lights
        self.graph.update_intersections()

        # 2. Update spawners
        for spawner in self.spawners:
            new_vehicle = spawner.update(self.graph)
            if new_vehicle:
                self.vehicles.append(new_vehicle)
                if config.DEBUG:
                    debug_log(f"Spawned vehicle {new_vehicle.id} at {spawner.node}")

        # 3. Update edges
        for src, dst, edge in edges_to_update:
            if hasattr(edge, 'cells'):
                if not any(cell is not None for cell in edge.cells):
                    continue
            elif hasattr(edge, 'vehicles'):
                if not edge.vehicles:
                    continue

            edge.update()

            if hasattr(edge, 'peek_last_vehicle') and edge.peek_last_vehicle():
                vehicle = edge.peek_last_vehicle()

                can_pass = True
                intersection = self.graph.get_intersection(dst)
                if intersection:
                    can_pass = intersection.can_pass(src)

                if not can_pass:
                    continue

                vehicle.pop_next_target()
                next_node = vehicle.next_target()

                if next_node is None:
                    edge.pop_last_vehicle()
                    self.remove_vehicle_safely(vehicle)
                else:
                    try:
                        next_edge = self.graph.get_edge(dst, next_node)

                        if next_edge.insert_vehicle(vehicle):
                            edge.pop_last_vehicle()
                            vehicle.current_edge = next_edge
                        else:
                            vehicle.path.insert(0, next_node)

                    except RuntimeError:
                        if config.DEBUG:
                            debug_log(f"Vehicle {vehicle.id} removed due to invalid path", "error")
                        edge.pop_last_vehicle()
                        self.remove_vehicle_safely(vehicle)

    def tick(self):
        """
        Appelé par la boucle principale (UI).
        """
        if self.visualizer:
            current_tick = self.t.value
            self.visualizer.update(current_tick)
            if not self.visualizer.handle_events():
                self.stop()
                return False
        return True
