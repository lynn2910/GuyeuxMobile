from time import sleep, time

from core.graph import RoadGraph


class Simulation:
    def __init__(self, graph, tps: int):
        self.graph = graph
        self.vehicles = []

        self.tps = tps
        self.tick_duration = 1.0 / tps

        self.t = 0
        self.running = False

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
        self.t += 1
        print(f"------ Tick {self.t} ------")
        start_time = time()

        self.internal_step()

        elapsed = time() - start_time
        wait_time = self.tick_duration - elapsed
        if wait_time > 0:
            sleep(wait_time)
        else:
            print(f"/!\\ Lag detected at tick '{self.t}' ({elapsed:.4f}s elapsed since last tick)")

    def internal_step(self):
        """
        Do all the work for one single update
        :return:
        """
        for src, dist, data in self.graph.get_edges():
            edge = data['object']
            exiting_vehicles = edge.update()

            print(f"\nEdge from {src} to {dist} :")
            edge.draw()
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
