class BaseEdge:
    """
    Abstract base class for all edge (road) models in the simulation.

    This class defines the common interface that all edge implementations must
    adhere to. It ensures that the simulation can interact with different types
    of road models (e.g., cellular automata, fluid dynamics) in a uniform way.
    """

    def __init__(self, distance: int):
        """
        Initializes the base properties of an edge.

        Args:
            distance (int): The length or capacity of the edge.
        """
        self.distance = int(distance)

    def update(self):
        """
        Advances the state of the edge by one time step.

        This method should implement the core logic of the traffic model,
        moving vehicles along the edge according to the model's rules.
        """
        raise NotImplementedError

    def insert_vehicle(self, vehicle) -> bool:
        """
        Tries to insert a vehicle at the beginning of the edge.

        Args:
            vehicle: The vehicle object to insert.

        Returns:
            True if the vehicle was successfully inserted, False otherwise (e.g., if the start is blocked).
        """
        raise NotImplementedError

    def peek_last_vehicle(self):
        """
        Returns the vehicle at the end of the edge without removing it.

        Returns:
            The vehicle object at the end, or None if no vehicle is ready to exit.
        """
        raise NotImplementedError

    def pop_last_vehicle(self):
        """
        Removes and returns the vehicle from the end of the edge.
        """
        raise NotImplementedError

    def draw_edge(self, src_pos: tuple, dst_pos: tuple, screen, vehicle_color):
        """
        Draws the current state of the edge using a graphical interface (e.g., Pygame).

        Args:
            src_pos (tuple): The (x, y) coordinates of the source node.
            dst_pos (tuple): The (x, y) coordinates of the destination node.
            screen: The drawing surface (e.g., a Pygame screen).
            vehicle_color: The color to use for drawing vehicles.
        """
        raise NotImplementedError

    def get_infos(self) -> list:
        """
        Returns a list of strings containing debug information about the edge's state.
        """
        raise NotImplementedError

    @staticmethod
    def evaluate_weight(src: str, dst: str, data: dict) -> float:
        """
        Calculates the weight (or cost) of traversing this edge for pathfinding algorithms.

        This static method is used by the A* algorithm to determine the best path.
        The weight can be based on distance, current congestion, etc.

        Args:
            src (str): The ID of the source node.
            dst (str): The ID of the destination node.
            data (dict): The edge's data dictionary from the graph.

        Returns:
            The calculated weight as a float.
        """
        raise NotImplementedError

    def get_occupation_ratio(self) -> float:
        """
        Calculates the occupancy of the edge as a normalized ratio.

        Returns:
            A float between 0.0 (empty) and 1.0 (full).
        """
        raise NotImplementedError
