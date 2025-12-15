import random
import pygame
from models.edges.base_edge import BaseEdge


class CellularEdge(BaseEdge):
    def __init__(self, distance: int, vmax: int, prob_slow: float):
        super().__init__(distance)
        self.vmax = vmax
        self.prob_slow = prob_slow
        self.cells = [None] * self.distance
        # PLUS DE QUEUE INTERNE : Si c'est plein, c'est plein.

    def insert_vehicle(self, vehicle):
        """
        Tente d'insérer au début. Retourne False si la première case est prise.
        """
        if self.cells[0] is None:
            self.cells[0] = vehicle
            vehicle.speed = min(vehicle.speed, self.vmax)
            return True
        return False

    def update(self) -> None:
        """
        Avance les véhicules. Ne retourne plus rien !
        Les véhicules arrivés au bout restent bloqués à la dernière case.
        """
        # On parcourt de la fin vers le début
        for pos in range(self.distance - 1, -1, -1):
            vehicle = self.cells[pos]
            if vehicle is None:
                continue

            # La distance max est la fin de la route
            # Si un véhicule est déjà au bout (pos == distance -1), il ne bouge pas.
            if pos == self.distance - 1:
                vehicle.speed = 0
                continue

            # Trouver l'obstacle suivant (soit un autre véhicule, soit la fin de la route)
            obstacle_pos = self.distance
            for search in range(pos + 1, self.distance):
                if self.cells[search] is not None:
                    obstacle_pos = search
                    break

            # Distance libre
            gap = obstacle_pos - pos - 1

            # Nagel-Schreckenberg classique
            # 1. Accélération
            vehicle.speed = min(vehicle.speed + 1, self.vmax)
            # 2. Freinage pour ne pas taper
            vehicle.speed = min(vehicle.speed, gap)
            # 3. Ralentissement aléatoire
            if random.random() < self.prob_slow and vehicle.speed > 0:
                vehicle.speed = max(0, vehicle.speed - 1)

            # Mouvement
            new_pos = pos + vehicle.speed

            if new_pos != pos:
                self.cells[new_pos] = vehicle
                self.cells[pos] = None

    def has_vehicle_at_exit(self) -> bool:
        """Vérifie s'il y a un véhicule prêt à sortir (dernière cellule)"""
        return self.cells[self.distance - 1] is not None

    def peek_last_vehicle(self):
        """Regarde le véhicule en bout de file sans l'enlever"""
        return self.cells[self.distance - 1]

    def pop_last_vehicle(self):
        """Enlève le véhicule de la dernière cellule (il a réussi à sortir)"""
        v = self.cells[self.distance - 1]
        self.cells[self.distance - 1] = None
        return v

    # ... (Gardez draw_console, draw_edge, get_infos, evaluate_weight identiques) ...
    # Je ne remets pas le code d'affichage ici pour alléger, il ne change pas
    # Sauf draw_edge où vous itérez self.cells normalement.

    def draw_console(self):
        for cell in self.cells:
            print("|", end="")
            print("o" if cell else " ", end="")
        print("|")

    def draw_edge(self, src_pos: tuple, dst_pos: tuple, screen, vehicle_color):
        for i, cell in enumerate(self.cells):
            if cell is not None:
                t = (i + 0.5) / self.distance
                x = src_pos[0] + t * (dst_pos[0] - src_pos[0])
                y = src_pos[1] + t * (dst_pos[1] - src_pos[1])
                pygame.draw.circle(screen, vehicle_color, (int(x), int(y)), 5)

    def get_infos(self) -> list:
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
        num_vehicles = sum(1 for c in self.cells if c is not None)
        return num_vehicles / self.distance if self.distance > 0 else 0.0

    @staticmethod
    def evaluate_weight(src, dst, data):
        edge = data['object']
        num = sum(1 for c in edge.cells if c)
        occ = num / edge.distance
        # Pénalité exponentielle pour éviter les bouchons
        return edge.distance * (1 + occ * 10)
