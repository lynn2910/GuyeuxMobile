class BaseEdge:
    """
    The base class for all edges of the road.
    :param distance: The distance of the edge (road).
    """

    def __init__(self, distance: int):
        self.distance = distance

    def update(self) -> list:
        """
        Updates the traffic on the edge.
        :return: Returns a list of vehicles that reached the end.
        """
        raise NotImplementedError

    @staticmethod
    def evaluate_weight(src: str, dst: str, data):
        """
        Evaluates the traffic on the edge, based on the source, destination, and the edge data.
        :param src: The source of the edge.
        :param dst: The destination of the edge.
        :param data: The data of the edge.
        :return: The calculated weight
        """
        raise NotImplementedError
