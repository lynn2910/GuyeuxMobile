class BaseIntersection:
    """
    Abstract base class for all intersection logic models in the simulation.

    This class defines the common interface that all intersection controllers
    must adhere to. It allows the simulation to manage different types of
    intersections (e.g., traffic lights, stop signs, roundabouts) uniformly.
    """

    def __init__(self, node_id: str):
        """
        Initializes the intersection logic for a specific node in the graph.

        Args:
            node_id (str): The ID of the graph node this intersection logic is attached to.
        """
        self.node_id = node_id

    def update(self):
        """
        Updates the internal state of the intersection.

        This method is called on every simulation tick and should implement
        the logic for the intersection's state changes (e.g., cycling traffic lights).
        """
        pass  # Default behavior is to do nothing.

    def can_pass(self, src_node: str) -> bool:
        """
        Determines if a vehicle arriving from a specific incoming road can cross the intersection.

        Args:
            src_node (str): The ID of the node from which the vehicle is arriving.

        Returns:
            True if passage is allowed (e.g., green light), False otherwise.
            By default, all traffic is allowed to pass.
        """
        return True

    def get_state(self, src_node: str) -> str:
        """
        Returns a string representing the visual state for a given incoming road.

        This is used by the UI to display the correct signal (e.g., "GREEN", "RED").

        Args:
            src_node (str): The ID of the node from which the traffic is arriving.

        Returns:
            A string descriptor of the state (e.g., "GREEN").
        """
        return "GREEN"
