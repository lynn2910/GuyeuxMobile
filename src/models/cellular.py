from queue import Queue

import pygame

from models.base import BaseEdge


class CellularEdge(BaseEdge):
    def __init__(self, distance: int, vmax: int, prob_slow: float):
        """
        Initialize the cellular structure for the edge.
        :param distance: The distance of the road
        :param vmax: The maximum speed allowed for a vehicle
        :param prob_slow: The probability of slowing down a vehicle
        """
        super().__init__(distance)
        self.vmax = vmax
        self.prob_slow = prob_slow
        self.cells = [None] * self.distance

        self.entry_queue = Queue()

    def insert_vehicle(self, vehicle):
        """
        Insert a vehicle at the beginning of the edge (position 0) or to the queue.
        """
        if self.cells[0] is None:
            self.cells[0] = vehicle
            vehicle.speed = min(vehicle.speed, self.vmax)
        else:
            self.entry_queue.put(vehicle)
            print(f"Warning: Vehicle {vehicle.id} trying to enter blocked edge, putting it in the queue")

    def update(self) -> list:
        exiting = []

        last_vehicle_pos = self.distance + 1

        # From right to left
        # That way, we're sure that the cars at the outer edge will move BEFORE the car behind (no collision :D)
        for pos in range(self.distance - 1, -1, -1):
            # TODO applying prob_slow
            vehicle = self.cells[pos]
            if vehicle is None:
                continue

            # Update the car speed to be either right behind the next car,
            # or to go faster, until it reaches the vmax
            distance_to_next = last_vehicle_pos - pos - 1
            vehicle.speed = min(distance_to_next, vehicle.speed + 1, self.vmax)

            # Update the car pos, and make the car exit the edge if required to
            next_pos = pos + vehicle.speed
            if next_pos >= self.distance:
                exiting.append(vehicle)
                self.cells[pos] = None
            else:
                if self.cells[next_pos] is None:
                    self.cells[next_pos] = vehicle
                    self.cells[pos] = None

            last_vehicle_pos = next_pos

        # Add a vehicle from the queue if any
        if not self.entry_queue.empty() and self.cells[0] is None:
            self.cells[0] = self.entry_queue.get_nowait()

        return exiting

    def draw_console(self):
        for cell in self.cells:
            print("|", end="")
            print("o" if cell else " ", end="")
        print("|")

    def draw_edge(self, src_pos: tuple, dst_pos: tuple, screen, vehicle_color):
        """
        Draw the vehicles on the road
        :param src_pos: (x, y) coordinates of the source node
        :param dst_pos: (x, y) coordinates of the destination node
        :param screen: Pygame surface
        :param vehicle_color: Vehicles color
        """
        for i, cell in enumerate(self.cells):
            if cell is not None:
                t = (i + 0.5) / self.distance

                x = src_pos[0] + t * (dst_pos[0] - src_pos[0])
                y = src_pos[1] + t * (dst_pos[1] - src_pos[1])

                pygame.draw.circle(screen, vehicle_color, (int(x), int(y)), 5)

                # font = pygame.font.Font(None, 14)
                # speed_text = font.render(str(cell.speed), True, (0, 0, 0))
                # screen.blit(speed_text, (int(x) + 7, int(y) - 5))

    def get_infos(self) -> list:
        """
        Return information about an edge
        :return: String list with the details
        """
        num_vehicles = sum(1 for cell in self.cells if cell is not None)
        queue_size = self.entry_queue.qsize()

        infos = [
            f"Vmax:       {self.vmax * 10} Km/h",
            f"Prob slow:  {int(self.prob_slow * 100)}%",
            f"Vehicles:   {num_vehicles}/{self.distance}",
        ]

        if queue_size > 0:
            infos.append(f"Queue:      {queue_size}")

        occupation_rate = (num_vehicles / self.distance) * 100
        infos.append(f"Occupation: {occupation_rate:.1f}%")

        return infos

    @staticmethod
    def evaluate_weight(src, dst, data):
        return data['object'].distance
