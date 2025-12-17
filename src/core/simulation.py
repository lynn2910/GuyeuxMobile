from time import sleep, time
import config
from cli import debug_log


class Simulation:
    """
    Manages the main simulation loop and state.
    OPTIMIZED VERSION with better performance.
    """

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

        # Cache des edges avec seulement ceux qui ont des véhicules
        self.active_edges_cache = []
        self.all_edges_cache = [
            (u, v, data['object'])
            for u, v, data in self.graph.get_edges()
        ]

        # Compteur pour mettre à jour le cache périodiquement
        self._cache_update_counter = 0

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

    def _update_active_edges_cache(self):
        """
        Met à jour le cache des edges actifs (contenant des véhicules).
        OPTIMIZATION: Évite d'itérer sur tous les edges à chaque tick.
        """
        self.active_edges_cache = [
            (src, dst, edge)
            for src, dst, edge in self.all_edges_cache
            if (hasattr(edge, 'vehicles') and edge.vehicles) or
               (hasattr(edge, 'cells') and any(cell is not None for cell in edge.cells))
        ]

    def internal_step(self):
        # Mettre à jour le cache tous les 10 ticks pour équilibrer performance/précision
        self._cache_update_counter += 1
        if self._cache_update_counter >= 10:
            self._update_active_edges_cache()
            self._cache_update_counter = 0

        # 1. Update traffic lights
        self.graph.update_intersections()

        # 2. Update spawners
        for spawner in self.spawners:
            new_vehicle = spawner.update(self.graph)
            if new_vehicle:
                self.vehicles.append(new_vehicle)
                if config.DEBUG:
                    debug_log(f"Spawned vehicle {new_vehicle.id} at {spawner.node}")

        # 3. Update edges - utiliser le cache si disponible, sinon tous les edges
        edges_to_update = self.active_edges_cache if self.active_edges_cache else self.all_edges_cache

        for src, dst, edge in edges_to_update:
            # Skip empty edges in cellular model
            if hasattr(edge, 'cells'):
                if not any(cell is not None for cell in edge.cells):
                    continue
            # Skip empty edges in fluid model
            elif hasattr(edge, 'vehicles'):
                if not edge.vehicles:
                    continue

            edge.update()

            # Vérifier si un véhicule peut passer à l'edge suivant
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
                        debug_log(f"Vehicle {vehicle.id} removed due to invalid path", "error")
                        edge.pop_last_vehicle()
                        self.remove_vehicle_safely(vehicle)
