from models.edges.base_edge import BaseEdge
from entities.vehicle import Vehicle
import random


class FluidEdge(BaseEdge):
    def __init__(self, distance: int, vmax: int, density_max: float = 0.2):
        super().__init__(distance)
        self.vmax = float(vmax)
        self.density_max = density_max
        self.max_vehicles = int(self.distance * self.density_max)
        self.vehicles = []
        self.positions = {}

    def insert_vehicle(self, vehicle: Vehicle):
        if len(self.vehicles) >= self.max_vehicles:
            return False

        self.vehicles.append(vehicle)
        self.positions[vehicle.id] = 0.0
        vehicle.speed = 0
        return True

    def update(self) -> None:
        count = len(self.vehicles)
        if count == 0:
            return

        # On triche un peu : on considère que la densité impacte la vitesse
        # moins vite au début pour garder du flux, puis chute brutalement.
        density = count / self.distance

        # Courbe de vitesse moins linéaire (permet de rouler un peu même si dense)
        # v = vmax * (1 - (rho/rho_max)^2)
        ratio = density / self.density_max
        speed_factor = max(0.0, 1.0 - (ratio ** 2))

        current_speed = self.vmax * speed_factor

        # Tri pour gérer les collisions
        sorted_vehicles = sorted(self.vehicles, key=lambda v: self.positions[v.id], reverse=True)

        for i, vehicle in enumerate(sorted_vehicles):
            current_pos = self.positions[vehicle.id]

            # Variance plus faible dans les bouchons
            variance = random.uniform(0.9, 1.1) if speed_factor > 0.2 else 1.0
            veh_speed = current_speed * variance

            new_pos = current_pos + veh_speed

            # 1. Limite : Fin de la route
            if new_pos > self.distance:
                new_pos = self.distance
                veh_speed = 0

                # 2. Limite : Véhicule de devant (Collisions)
            if i > 0:
                leader = sorted_vehicles[i - 1]
                leader_pos = self.positions[leader.id]

                # --- MODIFICATION ICI ---
                # Distance de sécurité réduite à 0.5m (au lieu de 1m)
                # Cela permet de tasser visuellement les voitures
                safe_distance = 0.5

                if new_pos >= leader_pos - safe_distance:
                    new_pos = leader_pos - safe_distance
                    veh_speed = 0

            self.positions[vehicle.id] = new_pos
            vehicle.speed = veh_speed

    def has_vehicle_at_exit(self) -> bool:
        # On cherche s'il y a au moins un véhicule 'collé' à la fin
        # Avec les flottants, on prend une petite marge (ex: > distance - 0.5)
        for v in self.vehicles:
            if self.positions[v.id] >= self.distance - 0.5:
                return True
        return False

    def peek_last_vehicle(self):
        # Retourne le véhicule le plus avancé s'il est à la sortie
        if not self.vehicles:
            return None

        # Le véhicule le plus avancé
        leader = max(self.vehicles, key=lambda v: self.positions[v.id])
        if self.positions[leader.id] >= self.distance - 0.5:
            return leader
        return None

    def pop_last_vehicle(self):
        leader = self.peek_last_vehicle()
        if leader:
            self.vehicles.remove(leader)
            del self.positions[leader.id]
            return leader
        return None

    def get_vehicle_positions(self):
        for v in self.vehicles:
            ratio = self.positions[v.id] / self.distance
            yield v, ratio

    def get_infos(self) -> list:
        count = len(self.vehicles)
        density = count / self.distance if self.distance > 0 else 0
        speed = self.vmax * (1.0 - (density / self.density_max)) if self.density_max > 0 else 0
        infos = [
            f"Type:       Fluide (LWR)",
            f"Vmax:       {self.vmax:.1f} m/t",
            f"Densité:    {density:.3f} v/m",
            f"V. Flux:    {speed:.1f} m/t",
            f"Véhicules:  {count}/{self.max_vehicles}",
            f"Occupation: {(count / max(self.max_vehicles, 1)) * 100:.1f}%"
        ]
        return infos

    def get_occupation_ratio(self) -> float:
        return len(self.vehicles) / max(self.max_vehicles, 1)

    @staticmethod
    def evaluate_weight(src, dst, data):
        edge = data['object']
        base_cost = edge.distance
        count = len(edge.vehicles)
        if count == 0: return base_cost / edge.vmax

        density = count / edge.distance
        speed_factor = max(0.01, 1.0 - (density / edge.density_max))
        return base_cost / (edge.vmax * speed_factor)
