from models.edges.base_edge import BaseEdge
from entities.vehicle import Vehicle
import random


class FluidEdge(BaseEdge):
    """
    An edge implementation based on a fluid-dynamics traffic model.

    This class simulates traffic as a continuous flow, inspired by the Lighthill-Whitham-Richards (LWR) model.
    Vehicle speed is a function of the local traffic density. Vehicles have continuous positions along the edge.
    """

    def __init__(self, distance: int, vmax: int, density_max: float = 0.2):
        """
        Initializes the fluid-dynamic edge.

        Args:
            distance (int): The length of the edge in meters.
            vmax (int): The maximum speed in meters per tick.
            density_max (float): The maximum density in vehicles per meter.
        """
        super().__init__(distance)
        self.vmax = float(vmax)
        self.density_max = density_max
        self.max_vehicles = int(self.distance * self.density_max)
        self.vehicles = []
        self.positions = {}  # Maps vehicle.id to its float position on the edge

    def insert_vehicle(self, vehicle: Vehicle) -> bool:
        """
        Tries to insert a vehicle at the beginning of the edge.

        Returns:
            False if the edge is at maximum capacity, True otherwise.
        """
        if len(self.vehicles) >= self.max_vehicles:
            return False

        self.vehicles.append(vehicle)
        self.positions[vehicle.id] = 0.0
        vehicle.speed = 0
        return True

    def update(self) -> None:
        """
        Updates vehicle positions based on a density-dependent speed function.
        """
        count = len(self.vehicles)
        if count == 0:
            return

        # --- LWR Model Core ---
        # Speed is a function of density. Here, we use a quadratic relationship.
        # v = vmax * (1 - (rho / rho_max)^2)
        # This allows for some speed even in dense traffic, with a sharp drop-off near max density.
        density = count / self.distance
        ratio = density / self.density_max
        speed_factor = max(0.0, 1.0 - (ratio ** 2))
        current_speed = self.vmax * speed_factor

        # Sort vehicles by position to handle front-to-back interactions.
        sorted_vehicles = sorted(self.vehicles, key=lambda v: self.positions[v.id], reverse=True)

        for i, vehicle in enumerate(sorted_vehicles):
            current_pos = self.positions[vehicle.id]

            # Introduce slight randomness to vehicle speed, reduced in heavy traffic.
            variance = random.uniform(0.9, 1.1) if speed_factor > 0.2 else 1.0
            veh_speed = current_speed * variance

            new_pos = current_pos + veh_speed

            # Boundary condition 1: Do not overshoot the end of the road.
            if new_pos > self.distance:
                new_pos = self.distance
                veh_speed = 0

            # Boundary condition 2: Do not collide with the vehicle in front.
            if i > 0:
                leader = sorted_vehicles[i - 1]
                leader_pos = self.positions[leader.id]
                safe_distance = 0.5  # Minimal visual gap between vehicles

                if new_pos >= leader_pos - safe_distance:
                    new_pos = leader_pos - safe_distance
                    veh_speed = 0

            self.positions[vehicle.id] = new_pos
            vehicle.speed = veh_speed

    def peek_last_vehicle(self):
        """
        Returns the most advanced vehicle if it is at the exit, without removing it.
        """
        if not self.vehicles:
            return None

        # Find the vehicle with the maximum position.
        leader = max(self.vehicles, key=lambda v: self.positions[v.id])
        # Check if it's close enough to the end to be considered "at the exit".
        if self.positions[leader.id] >= self.distance - 0.5:
            return leader
        return None

    def pop_last_vehicle(self):
        """
        Removes and returns the vehicle at the exit of the edge.
        """
        leader = self.peek_last_vehicle()
        if leader:
            self.vehicles.remove(leader)
            del self.positions[leader.id]
            return leader
        return None

    def get_vehicle_positions(self):
        """
        Returns a generator of (vehicle, position_ratio) for rendering.
        """
        if not self.vehicles or self.distance == 0:
            return

        for vehicle in self.vehicles:
            pos = self.positions.get(vehicle.id, 0.0)
            yield vehicle, pos / self.distance

    def get_infos(self) -> list:
        """Returns a list of strings with statistics about the edge."""
        count = len(self.vehicles)
        density = count / self.distance if self.distance > 0 else 0
        # Calculate the theoretical speed based on current density
        speed = self.vmax * max(0.0, 1.0 - (density / self.density_max) ** 2) if self.density_max > 0 else 0
        infos = [
            f"Type:       Fluid (LWR)",
            f"Vmax:       {self.vmax:.1f} m/t",
            f"Density:    {density:.3f} v/m",
            f"Flow Speed: {speed:.1f} m/t",
            f"Vehicles:   {count}/{self.max_vehicles}",
            f"Occupation: {(count / max(self.max_vehicles, 1)) * 100:.1f}%"
        ]
        return infos

    def get_occupation_ratio(self) -> float:
        """Calculates the fraction of the edge's capacity that is used."""
        return len(self.vehicles) / max(self.max_vehicles, 1)

    @staticmethod
    def evaluate_weight(src, dst, data) -> float:
        """
        Calculates the travel time for this edge, penalizing congestion.
        Used for A* pathfinding.
        """
        edge = data['object']
        # Travel time = distance / speed.
        base_time = edge.distance / edge.vmax if edge.vmax > 0 else float('inf')

        count = len(edge.vehicles)
        if count == 0:
            return base_time

        # Calculate speed based on current density
        density = count / edge.distance
        speed_factor = max(0.01, 1.0 - (density / edge.density_max) ** 2)  # Avoid division by zero
        current_speed = edge.vmax * speed_factor

        if current_speed <= 0:
            return -1

        return edge.distance / current_speed
