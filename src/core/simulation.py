from time import sleep, time

import config
from cli import debug_log


class Simulation:
    def __init__(self, graph, tps: float, visualizer=None):
        self.graph = graph
        self.vehicles = []

        self.tps = tps
        self.tick_duration = 1.0 / tps

        self.t = 0
        self.running = False

        self.since_last_update = 0

        self.visualizer = visualizer

    def add_vehicle(self, vehicle, start_edge):
        """
        Add a vehicle to the simulation, inserting it to the desired edge.
        :param vehicle: Vehicle object
        :param start_edge:
        :return:
        """
        vehicle.current_edge = start_edge
        start_edge.insert_vehicle(vehicle)
        self.vehicles.append(vehicle)

    def tick(self):
        """
        The main loop of the simulation.
        :return:
        """
        print(self.since_last_update)
        start_time = time()

        is_a_sim_update_tick = False
        if self.since_last_update >= self.tps:
            self.t += 1
            print(f"------ Tick {self.t} ------")
            
            self.internal_step()
            self.since_last_update = 0
            is_a_sim_update_tick = True

        if self.visualizer:
            self.visualizer.update(self.t)
            if not self.visualizer.handle_events():
                self.running = False
                return

        if not is_a_sim_update_tick:
            elapsed = time() - start_time
            self.since_last_update += elapsed

        # wait_time = self.tick_duration - elapsed
        # if wait_time > 0:
        #     sleep(wait_time)
        # else:
        #     print(f"/!\\ Lag detected at tick '{self.t}' ({elapsed:.4f}s elapsed since last tick)")

    def internal_step(self):
        """
        Do all the work for one single update
        :return:
        """
        for src, dist, data in self.graph.get_edges():
            edge = data['object']
            exiting_vehicles = edge.update()

            if config.DEBUG:
                print(f"\nEdge from {src} to {dist} :")
                edge.draw_console()
                print(f"{len(exiting_vehicles)} exiting vehicles")

            # Redirecting all vehicles to the next edge or remove them
            for vehicle in exiting_vehicles:
                vehicle.pop_next_target()
                next_node = vehicle.next_target()

                if next_node is None:
                    # The vehicle is out-of-bound, we can remove its existence
                    self.vehicles.remove(vehicle)
                else:
                    current_node = dist
                    next_edge = self.graph.get_edge(current_node, next_node)
                    vehicle.current_edge = next_edge
                    next_edge.insert_vehicle(vehicle)
