import random
import pygame
from models.edges.base_edge import BaseEdge


class CellularEdge(BaseEdge):
    """
    An edge implementation based on a 1D cellular automaton model.

    This class simulates traffic flow using the Nagel-Schreckenberg model, where the
    road is divided into discrete cells that can either be empty or occupied by a single vehicle.
    """

    def __init__(self, distance: int, vmax: int, prob_slow: float):
        """
        Initializes the cellular edge.

        Args:
            distance (int): The number of cells on the edge.
            vmax (int): The maximum speed (in cells per tick) a vehicle can achieve.
            prob_slow (float): The probability of a vehicle randomly slowing down.
        """
        super().__init__(distance)
        self.vmax = vmax
        self.prob_slow = prob_slow
        self.cells = [None] * self.distance  # Represents the road as a list of cells

    def insert_vehicle(self, vehicle) -> bool:
        """
        Tries to insert a vehicle at the beginning of the edge.

        Returns:
            False if the first cell is already occupied, True otherwise.
        """
        if self.cells[0] is None:
            self.cells[0] = vehicle
            vehicle.speed = min(vehicle.speed, self.vmax)
            return True
        return False

    def update(self) -> None:
        """
        Updates the state of all vehicles on the edge according to the Nagel-Schreckenberg model.
        The update is performed from the end of the road to the beginning to avoid conflicts.
        """
        # Iterate from the end of the road to the beginning.
        for pos in range(self.distance - 1, -1, -1):
            vehicle = self.cells[pos]
            if vehicle is None:
                continue

            # If a vehicle is already at the last cell, it cannot move further on this edge.
            if pos == self.distance - 1:
                vehicle.speed = 0
                continue

            # Find the next obstacle (either another vehicle or the end of the road).
            obstacle_pos = self.distance
            for search in range(pos + 1, self.distance):
                if self.cells[search] is not None:
                    obstacle_pos = search
                    break

            # Calculate the number of free cells ahead.
            gap = obstacle_pos - pos - 1

            vehicle.speed = min(vehicle.speed + 1, self.vmax)
            vehicle.speed = min(vehicle.speed, gap)

            if random.random() < self.prob_slow and vehicle.speed > 0:
                vehicle.speed = max(0, vehicle.speed - 1)

            new_pos = pos + vehicle.speed
            if new_pos != pos:
                self.cells[new_pos] = vehicle
                self.cells[pos] = None

    def peek_last_vehicle(self):
        """Returns the vehicle in the last cell without removing it."""
        return self.cells[self.distance - 1]

    def pop_last_vehicle(self):
        """Removes and returns the vehicle from the last cell."""
        v = self.cells[self.distance - 1]
        self.cells[self.distance - 1] = None
        return v

    def draw_console(self):
        """Prints a simple text representation of the edge to the console."""
        for cell in self.cells:
            print("|", end="")
            print("o" if cell else " ", end="")
        print("|")

    def draw_edge(self, src_pos: tuple, dst_pos: tuple, screen, vehicle_color):
        """Draws the vehicles on the edge using Pygame."""
        for i, cell in enumerate(self.cells):
            if cell is not None:
                # Interpolate position along the edge
                t = (i + 0.5) / self.distance
                x = src_pos[0] + t * (dst_pos[0] - src_pos[0])
                y = src_pos[1] + t * (dst_pos[1] - src_pos[1])
                pygame.draw.circle(screen, vehicle_color, (int(x), int(y)), 5)

    def get_infos(self) -> list:
        """Returns a list of strings with statistics about the edge."""
        num_vehicles = sum(1 for cell in self.cells if cell is not None)
        infos = [
            f"Type:       Cellular",
            f"Vmax:       {self.vmax * 10} Km/h",
            f"Prob slow:  {int(self.prob_slow * 100)}%",
            f"Vehicles:   {num_vehicles}/{self.distance}",
            f"Occupation: {(num_vehicles / self.distance) * 100:.1f}%"
        ]
        return infos

    def get_occupation_ratio(self) -> float:
        """Calculates the fraction of cells that are occupied."""
        num_vehicles = sum(1 for c in self.cells if c is not None)
        return num_vehicles / self.distance if self.distance > 0 else 0.0

    @staticmethod
    def evaluate_weight(src, dst, data) -> float:
        """
        Calculates the travel cost for this edge, heavily penalizing congestion.
        Used for A* pathfinding.
        """
        edge = data['object']
        # Calculate current occupancy
        num_vehicles = sum(1 for c in edge.cells if c is not None)
        occupancy = num_vehicles / edge.distance if edge.distance > 0 else 0
        # The weight is the base distance, increased exponentially with occupancy to deter pathfinding through jams.
        return edge.distance * (1 + occupancy ** 2 * 10)
