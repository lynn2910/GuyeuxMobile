from time import sleep, time
import config
from cli import debug_log


class Simulation:
    """
    Manages the main simulation loop and state.

    This class is responsible for initializing the simulation environment,
    running the simulation tick by tick, and coordinating updates between
    the graph, vehicles, and visualizer.
    """
    def __init__(self, graph, tps: float, visualizer=None):
        """
        Initializes the simulation.

        Args:
            graph: The graph representing the road network.
            tps (float): Ticks per second, determining the simulation's speed.
            visualizer: An optional visualizer object to render the simulation.
        """
        self.graph = graph
        self.vehicles = []
        self.spawners = []
        self.tps = tps
        self.tick_duration = 1.0 / tps
        self.t = 0  # Simulation time in ticks
        self.running = False
        self.since_last_update = 0
        self.visualizer = visualizer

    def add_vehicle(self, vehicle, start_edge):
        """Adds a vehicle to the simulation on a specified starting edge."""
        vehicle.current_edge = start_edge
        start_edge.insert_vehicle(vehicle)
        self.vehicles.append(vehicle)

    def add_spawner(self, spawner):
        """Adds a vehicle spawner to the simulation."""
        self.spawners.append(spawner)

    def remove_vehicle_safely(self, vehicle):
        """Safely removes a vehicle from the simulation."""
        try:
            self.vehicles.remove(vehicle)
        except ValueError:
            # Vehicle might have been already removed, so we can ignore.
            pass

    def tick(self):
        """
        Executes a single simulation tick.

        This method manages the simulation's timing to match the configured TPS.
        It calls the internal step for logic updates and tells the visualizer to redraw.
        """
        start_time = time()
        if self.since_last_update >= self.tick_duration:
            self.t += 1
            self.internal_step()
            self.since_last_update -= self.tick_duration

        if self.visualizer:
            self.visualizer.update(self.t)
            # Stop the simulation if the visualizer window is closed.
            if not self.visualizer.handle_events():
                self.running = False
                return
        
        elapsed = time() - start_time
        self.since_last_update += elapsed

    def internal_step(self):
        """
        Performs the core logic update for a single discrete time step.
        This includes updating traffic lights, spawning new vehicles, and moving
        existing vehicles across the graph.
        """
        # 1. Update traffic lights at intersections
        self.graph.update_intersections()

        # 2. Update vehicle spawners to generate new vehicles
        for spawner in self.spawners:
            new_vehicle = spawner.update(self.graph)
            if new_vehicle:
                self.vehicles.append(new_vehicle)
                if config.DEBUG:
                    debug_log(f"Spawned vehicle {new_vehicle.id} at {spawner.node}")

        # 3. Update edges and handle vehicle transfers between them
        for src, dst, data in self.graph.get_edges():
            edge = data['object']

            # First, update the positions of all vehicles currently on this edge.
            # Vehicles will move along the edge and queue up at the end if they cannot exit.
            edge.update()

            # Second, handle the transfer of vehicles from the end of this edge to the next.
            if hasattr(edge, 'peek_last_vehicle') and edge.peek_last_vehicle():
                vehicle = edge.peek_last_vehicle()

                # Check if the intersection ahead allows the vehicle to pass (e.g., green light).
                can_pass = True
                intersection = self.graph.get_intersection(dst)
                if intersection:
                    can_pass = intersection.can_pass(src)

                if not can_pass:
                    # Red light or blocked intersection: vehicle waits at the end of the current edge.
                    # By not popping it, it naturally blocks any vehicles behind it.
                    continue

                # The intersection is clear, now determine the next edge.
                vehicle.pop_next_target()  # Temporarily consume the next node in the path to see where to go.
                next_node = vehicle.next_target()

                if next_node is None:
                    # The vehicle has reached its final destination.
                    edge.pop_last_vehicle()
                    self.remove_vehicle_safely(vehicle)
                else:
                    # The vehicle needs to move to a connecting edge.
                    try:
                        next_edge = self.graph.get_edge(dst, next_node)

                        # Attempt to insert the vehicle into the next edge.
                        # This will fail if the next edge is already full.
                        if next_edge.insert_vehicle(vehicle):
                            # Transfer successful: remove vehicle from the old edge.
                            edge.pop_last_vehicle()
                            vehicle.current_edge = next_edge
                        else:
                            # Transfer failed (congestion ahead): The vehicle remains on the current edge.
                            # We must restore its path to the state before the failed transfer attempt.
                            vehicle.path.insert(0, next_node)

                    except RuntimeError:
                        # Pathfinding or map error: the planned route leads to a non-existent edge.
                        # The vehicle is removed from the simulation to prevent errors.
                        debug_log(f"Vehicle {vehicle.id} removed due to invalid path from {dst} to {next_node}", "error")
                        edge.pop_last_vehicle()
                        self.remove_vehicle_safely(vehicle)
