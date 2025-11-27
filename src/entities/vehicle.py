class Vehicle:
    def __init__(self, vehicle_id: int, path: list[str]):
        self.id = vehicle_id
        self.path = path
        self.current_edge = None
        self.speed = 0

    def next_target(self):
        if len(self.path) > 0:
            return self.path[0]
        return None

    def pop_next_target(self):
        if self.path:
            self.path.pop(0)
