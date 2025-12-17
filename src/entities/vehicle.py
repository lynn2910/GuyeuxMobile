class Vehicle:
    """
    Represents a single vehicle (or agent) in the traffic simulation.

    Each vehicle has a unique ID, a predetermined path to follow, and state
    variables such as its current location (edge) and speed.
    """

    def __init__(self, vehicle_id: str, path: list[str]):
        """
        Initializes a new vehicle.

        Args:
            vehicle_id (str): A unique identifier for the vehicle.
            path (list[str]): A list of node IDs representing the vehicle's
                              planned route, starting from the node after its
                              initial edge.
        """
        self.id = vehicle_id
        self.path = path
        self.current_edge = None  # The edge object the vehicle is currently on.
        self.speed = 0  # The vehicle's current speed.

    def next_target(self) -> str | None:
        """
        Returns the next node ID in the vehicle's path without consuming it.

        Returns:
            The next node ID as a string, or None if the path is empty.
        """
        if len(self.path) > 0:
            return self.path[0]
        return None

    def pop_next_target(self):
        """
        Consumes the next node in the path.

        This is called when the vehicle successfully moves to the next edge
        in its route.
        """
        if self.path:
            self.path.pop(0)
