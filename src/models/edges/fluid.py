# models/fluid.py
from models.edges.base_edge import BaseEdge
from entities.vehicle import Vehicle
import random


class FluidEdge(BaseEdge):
    def __init__(self, distance: int, vmax: int, density_max: float = 0.2):
        """
        Initialise une arête fluide (Modèle Lighthill-Whitham-Richards simplifié).
        :param distance: Longueur de la route en mètres.
        :param vmax: Vitesse maximale (m/tick).
        :param density_max: Densité maximale (véhicules/mètre). 0.2 ~= 1 voiture tous les 5m.
        """
        super().__init__(distance)
        self.vmax = float(vmax)
        self.density_max = density_max

        # Capacité max théorique (Jam density)
        self.max_vehicles = int(self.distance * self.density_max)

        # Stockage : Liste des véhicules présents et dictionnaire de leurs positions
        self.vehicles = []
        self.positions = {}  # {vehicle_id: float_position}

    def insert_vehicle(self, vehicle: Vehicle):
        """
        Tente d'insérer un véhicule au début de l'arête.
        Retourne True si succès, False si l'arête est saturée.
        """
        if len(self.vehicles) >= self.max_vehicles:
            # Route saturée, on refuse l'insertion
            return False

        self.vehicles.append(vehicle)
        self.positions[vehicle.id] = 0.0
        vehicle.speed = 0  # Sera mis à jour au prochain update
        return True

    def update(self) -> list:
        """
        Mise à jour selon le modèle de Greenshields avec vitesse minimale garantie.
        """
        exiting = []

        # 1. Calcul de la densité actuelle (k)
        count = len(self.vehicles)
        if count == 0:
            return exiting

        density = count / self.distance

        # --- CORRECTION ICI ---
        # On calcule le facteur de ralentissement (1.0 = fluide, 0.0 = bouché)
        speed_factor = 1.0 - (density / self.density_max)

        # On empêche le facteur de tomber à 0 absolu.
        # On garde toujours au moins 5% ou 10% de la vitesse (vitesse de "crawl")
        # Sinon le bouchon ne se résorbe jamais.
        speed_factor = max(0.1, speed_factor)

        # 2. Calcul de la vitesse globale
        current_speed = self.vmax * speed_factor

        # 3. Mise à jour des positions
        # On itère sur une copie pour pouvoir modifier la liste originale sans bug
        for vehicle in list(self.vehicles):
            current_pos = self.positions[vehicle.id]

            # Variance : plus naturelle.
            # On évite que des voitures doublent trop violemment dans un bouchon.
            if speed_factor < 0.3:
                # Dans les bouchons, variance faible (tout le monde se suit)
                variance = random.uniform(0.9, 1.1)
            else:
                # Fluide, variance plus libre
                variance = random.uniform(0.85, 1.15)

            # Vitesse finale du véhicule pour ce tick
            veh_speed = current_speed * variance
            vehicle.speed = veh_speed  # Mise à jour pour le visualiseur

            # Nouvelle position
            new_pos = current_pos + veh_speed

            if new_pos >= self.distance:
                # Le véhicule sort
                exiting.append(vehicle)
                self.vehicles.remove(vehicle)
                del self.positions[vehicle.id]
            else:
                self.positions[vehicle.id] = new_pos

        return exiting

    def get_vehicle_positions(self):
        """Retourne un itérateur de (Vehicle, position_ratio 0..1) pour le rendu"""
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

    @staticmethod
    def evaluate_weight(src, dst, data):
        """
        Pour le pathfinding, le poids est dynamique selon la congestion.
        """
        edge = data['object']
        base_cost = edge.distance

        # Pénalité de congestion : Coût = Distance / Vitesse_Actuelle
        count = len(edge.vehicles)

        if count == 0:
            return base_cost / edge.vmax  # Temps minimal

        density = count / edge.distance
        speed_factor = 1.0 - (density / edge.density_max)

        # Éviter division par zéro
        if speed_factor <= 0.01:
            speed_factor = 0.01

        # Coût = distance / vitesse effective
        return base_cost / (edge.vmax * speed_factor)

    def get_occupation_ratio(self) -> float:
        """Retourne le ratio d'occupation normalisé [0,1]"""
        return len(self.vehicles) / max(self.max_vehicles, 1)
