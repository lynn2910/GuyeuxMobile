from typing import List

from models.intersections.base_intersection import BaseIntersection


class TrafficLightIntersection(BaseIntersection):
    def __init__(self, node_id: str, incoming_nodes: List[str], duration: int = 50):
        """
        Un feu tricolore simple qui alterne le vert sur chaque route entrante une par une (Round Robin).

        :param incoming_nodes: Liste des IDs des nœuds connectés qui entrent vers ce nœud.
        :param duration: Durée du feu vert en ticks.
        """
        super().__init__(node_id)
        self.incoming_nodes = incoming_nodes
        self.duration = duration

        # État interne
        self.current_green_idx = 0  # Quel index de incoming_nodes a le feu vert
        self.timer = 0

    def update(self):
        if not self.incoming_nodes:
            return

        self.timer += 1

        # Changement de feu
        if self.timer >= self.duration:
            self.timer = 0
            self.current_green_idx = (self.current_green_idx + 1) % len(self.incoming_nodes)

    def can_pass(self, src_node: str) -> bool:
        if not self.incoming_nodes:
            return True

        # Seul le noeud qui a l'index actif a le droit de passer
        active_node = self.incoming_nodes[self.current_green_idx]
        return src_node == active_node

    def get_state(self, src_node: str) -> str:
        if not self.incoming_nodes:
            return "GREEN"

        active_node = self.incoming_nodes[self.current_green_idx]
        return "GREEN" if src_node == active_node else "RED"
