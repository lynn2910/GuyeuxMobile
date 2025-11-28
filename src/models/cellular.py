from queue import Queue

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

    def draw(self):
        for cell in self.cells:
            print("|", end="")
            print("o" if cell else " ", end="")
        print("|")

    @staticmethod
    def evaluate_weight(src, dst, data):
        return data['object'].distance
