from typing import List, Optional


class BaseIntersection:
    def __init__(self, node_id: str):
        self.node_id = node_id

    def update(self):
        """
        Met à jour l'état de l'intersection (ex: changer les feux).
        Appelé à chaque tick de simulation.
        """
        pass

    def can_pass(self, src_node: str) -> bool:
        """
        Vérifie si un véhicule venant de 'src_node' a le droit de traverser l'intersection.
        :param src_node: L'ID du nœud d'où vient le véhicule.
        :return: True si le passage est autorisé (Vert), False sinon (Rouge).
        """
        return True  # Par défaut, tout le monde passe

    def get_state(self, src_node: str) -> str:
        """
        Retourne l'état visuel pour l'interface (RED, GREEN, YELLOW).
        """
        return "GREEN"
