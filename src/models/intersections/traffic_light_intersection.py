from typing import List

from models.intersections.base_intersection import BaseIntersection


class TrafficLightIntersection(BaseIntersection):
    """
    Implements a simple traffic light controller for an intersection.

    This controller uses a round-robin algorithm, giving a green light to each
    incoming road one by one for a fixed duration.
    """
    def __init__(self, node_id: str, incoming_nodes: List[str], duration: int = 50):
        """
        Initializes the traffic light intersection.

        Args:
            node_id (str): The ID of the graph node this intersection is attached to.
            incoming_nodes (List[str]): A list of node IDs that have edges leading into this intersection.
            duration (int): The duration (in simulation ticks) for which the light stays green for each road.
        """
        super().__init__(node_id)
        self.incoming_nodes = incoming_nodes
        self.duration = duration

        # Internal state
        self.current_green_idx = 0  # Index into incoming_nodes that currently has a green light.
        self.timer = 0              # Timer to track the duration of the current green light.

    def update(self):
        """
        Updates the state of the traffic light.

        This method increments the timer and cycles the green light to the next
        incoming road when the duration is reached.
        """
        if not self.incoming_nodes:
            return

        self.timer += 1

        # Time to switch to the next light.
        if self.timer >= self.duration:
            self.timer = 0
            # Move to the next incoming node in the list, wrapping around if necessary.
            self.current_green_idx = (self.current_green_idx + 1) % len(self.incoming_nodes)

    def can_pass(self, src_node: str) -> bool:
        """
        Checks if a vehicle arriving from src_node is allowed to pass.

        Returns:
            True only if the traffic light for the road from src_node is currently green.
        """
        if not self.incoming_nodes:
            return True  # If there are no controlled incoming roads, allow all traffic.

        # The currently active node is the one at the green index.
        active_node = self.incoming_nodes[self.current_green_idx]
        return src_node == active_node

    def get_state(self, src_node: str) -> str:
        """
        Returns the current light state ("GREEN" or "RED") for a given incoming road.
        """
        if not self.incoming_nodes:
            return "GREEN"

        active_node = self.incoming_nodes[self.current_green_idx]
        return "GREEN" if src_node == active_node else "RED"
