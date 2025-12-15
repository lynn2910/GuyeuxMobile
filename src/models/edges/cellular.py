from queue import Queue
import random
import pygame

from models.edges.base_edge import BaseEdge


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
        Returns True if successfully inserted, False if queued.
        """
        if self.cells[0] is None:
            self.cells[0] = vehicle
            vehicle.speed = min(vehicle.speed, self.vmax)
            return True
        else:
            self.entry_queue.put(vehicle)
            return False  # Vehicle was queued, not immediately inserted

    def update(self, allow_exit: bool = True) -> list:
        """
        :param allow_exit: Si False (Feu Rouge), les véhicules ne peuvent pas sortir.
        """
        exiting = []
        last_vehicle_pos = self.distance + 1  # Position virtuelle bloquante

        # Si le feu est rouge, la 'barrière' est à la position distance
        if not allow_exit:
            last_vehicle_pos = self.distance

        # Parcours de la fin vers le début (Right to Left)
        for pos in range(self.distance - 1, -1, -1):
            vehicle = self.cells[pos]
            if vehicle is None:
                continue

            # Calcul de la distance libre devant
            distance_to_next = last_vehicle_pos - pos - 1

            # Accélération / Freinage
            vehicle.speed = min(distance_to_next, vehicle.speed + 1, self.vmax)

            # Probabilité de ralentissement (random brake)
            if random.random() < self.prob_slow and vehicle.speed > 0:
                vehicle.speed = max(0, vehicle.speed - 1)

            # Calcul nouvelle position
            next_pos = pos + vehicle.speed

            # --- LOGIQUE DE SORTIE ---
            if next_pos >= self.distance:
                if allow_exit:
                    # FEU VERT : On sort
                    exiting.append(vehicle)
                    self.cells[pos] = None
                    # On ne met pas à jour last_vehicle_pos car le véhicule est parti
                else:
                    # FEU ROUGE : On ne devrait pas arriver ici car last_vehicle_pos bloque
                    # Mais par sécurité, on force l'arrêt à la dernière case
                    target = self.distance - 1
                    if target != pos:  # Si on n'y est pas déjà
                        self.cells[target] = vehicle
                        self.cells[pos] = None
                    vehicle.speed = 0
                    last_vehicle_pos = target  # Ce véhicule devient l'obstacle pour le suivant
            else:
                # DÉPLACEMENT INTERNE
                if self.cells[next_pos] is None:
                    self.cells[next_pos] = vehicle
                    self.cells[pos] = None

                # Mise à jour de la position du dernier véhicule vu
                # (Sert d'obstacle pour l'itération suivante de la boucle)
                last_vehicle_pos = next_pos if self.cells[next_pos] else pos

        # Entrée des nouveaux véhicules depuis la queue
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

    def get_infos(self) -> list:
        """
        Return information about an edge
        :return: String list with the details
        """
        num_vehicles = sum(1 for cell in self.cells if cell is not None)
        queue_size = self.entry_queue.qsize()

        infos = [
            f"Type:       Cellular",
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
        """
        Évalue le poids d'une edge pour le pathfinding.
        Pour cellular, on pénalise les routes très occupées.
        """
        edge = data['object']
        base_cost = edge.distance

        # Pénalité basée sur l'occupation
        num_vehicles = sum(1 for cell in edge.cells if cell is not None)
        occupation = num_vehicles / edge.distance

        # Si occupation > 80%, on augmente fortement le coût
        if occupation > 0.8:
            return base_cost * 3.0
        elif occupation > 0.5:
            return base_cost * 1.5

        return base_cost

    def get_occupation_ratio(self) -> float:
        """Retourne le ratio d'occupation normalisé [0,1]"""
        num_vehicles = sum(1 for c in self.cells if c is not None)
        return num_vehicles / self.distance if self.distance > 0 else 0.0
