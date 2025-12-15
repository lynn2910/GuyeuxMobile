# models/fluid.py
from models.base import BaseEdge
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
        # On utilise une liste pour l'ordre (FIFO)
        self.vehicles = []
        self.positions = {}  # {vehicle_id: float_position}

    def insert_vehicle(self, vehicle: Vehicle):
        """
        Tente d'insérer un véhicule au début de l'arête.
        Retourne False si l'arête est saturée (Jam density atteinte).
        """
        if len(self.vehicles) >= self.max_vehicles:
            # Route saturée, bouchon à l'entrée
            return False

        self.vehicles.append(vehicle)
        self.positions[vehicle.id] = 0.0
        vehicle.speed = 0  # Sera mis à jour au prochain update
        return True

    def update(self) -> list:
        """
        Mise à jour selon le modèle de Greenshields.
        v = vmax * (1 - k/k_jam)
        """
        exiting = []

        # 1. Calcul de la densité actuelle (k)
        count = len(self.vehicles)
        if count == 0:
            return exiting

        density = count / self.distance

        # 2. Calcul de la vitesse globale du flux pour ce tick
        # On s'assure que la vitesse ne soit jamais négative
        current_speed = self.vmax * (1.0 - (density / self.density_max))
        current_speed = max(0.0, current_speed)

        # Facteur aléatoire mineur pour éviter la synchronisation parfaite (optionnel)
        # current_speed *= random.uniform(0.9, 1.1)

        # 3. Mise à jour des positions
        # On parcourt une copie pour pouvoir modifier la liste originale
        for vehicle in list(self.vehicles):
            current_pos = self.positions[vehicle.id]

            # Mise à jour de la vitesse du véhicule (pour info/visuel)
            vehicle.speed = current_speed * random.uniform(0.95, 1.05)

            # Nouvelle position
            new_pos = current_pos + current_speed

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
        density = count / self.distance
        speed = self.vmax * (1.0 - (density / self.density_max))

        infos = [
            f"Type:       Fluide (LWR)",
            f"Vmax:       {self.vmax:.1f} m/t",
            f"Densité:    {density:.3f} v/m",
            f"V. Flux:    {speed:.1f} m/t",
            f"Véhicules:  {count}/{self.max_vehicles}",
            f"Occupation: {(count / self.max_vehicles) * 100:.1f}%"
        ]
        return infos

    @staticmethod
    def evaluate_weight(src, dst, data):
        # Pour le pathfinding, le poids peut être dynamique selon la congestion !
        edge = data['object']
        base_cost = edge.distance

        # Pénalité de congestion : Coût = Distance / Vitesse_Actuelle
        # Si vide : Coût = Distance / Vmax
        # Si plein : Coût augmente
        count = len(edge.vehicles)
        density = count / edge.distance

        factor = 1.0 - (density / edge.density_max)
        if factor <= 0.01: factor = 0.01  # Éviter division par zéro

        return base_cost / factor  # Plus c'est lent, plus le "poids" est grand

    def get_occupation_ratio(self) -> float:
        return len(self.vehicles) / self.max_vehicles
