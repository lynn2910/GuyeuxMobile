class BaseEdge:
    """
    The base class for all edges of the road.
    :param distance: The distance of the edge (road).
    """

    def __init__(self, distance: int):
        self.distance = int(distance)

    def update(self) -> list:
        """
        Updates the traffic on the edge.
        :return: Returns a list of vehicles that reached the end.
        """
        raise NotImplementedError

    def draw_console(self):
        """
        Draws the traffic on the edge in the stdout.
        :return:
        """
        raise NotImplementedError

    def draw_edge(self, src_pos: tuple, dst_pos: tuple, screen, vehicle_color):
        """
        Draws the traffic on the edge using pygame.
        :param vehicle_color:
        :param screen:
        :param src_pos: The source node coordinates
        :param dst_pos: The destination node coordinates
        :return:
        """
        raise NotImplementedError

    def get_infos(self) -> list:
        """
        Return details about an edge.
        :return: String list with the details
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
