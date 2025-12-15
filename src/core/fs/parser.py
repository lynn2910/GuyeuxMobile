from typing import List, Tuple

from core.fs.tokenizer import Token, TokenType, Tokenizer
from core.graph import RoadGraph
from entities.vehicle import Vehicle
from entities.vehicle_spawner import VehicleSpawner
from models.edges.cellular import CellularEdge
from models.edges.fluid import FluidEdge


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current_token(self) -> Token:
        if self.pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.pos]

    def advance(self):
        self.pos += 1

    def expect(self, token_type: TokenType) -> Token:
        token = self.current_token()
        if token.type != token_type:
            raise SyntaxError(f"Expected {token_type}, found {token.type} at line {token.line}")
        self.advance()
        return token

    def skip_newlines(self):
        while self.current_token().type == TokenType.NEWLINE:
            self.advance()

    def parse_graph(self) -> dict:
        self.skip_newlines()
        self.expect(TokenType.GRAPH)

        graph_type = "cellular"

        if self.current_token().type == TokenType.LPAREN:
            self.advance()
            token_val = self.expect(TokenType.IDENTIFIER)
            graph_type = token_val.value
            self.expect(TokenType.RPAREN)

        self.expect(TokenType.COLON)
        self.skip_newlines()

        nodes = {}
        edges = []

        while self.current_token().type in [TokenType.NODE, TokenType.UEDGE, TokenType.BEDGE]:
            if self.current_token().type == TokenType.NODE:
                node_id, x, y = self.parse_node()
                nodes[node_id] = (x, y)

            elif self.current_token().type in [TokenType.UEDGE, TokenType.BEDGE]:
                edge_type = self.current_token().type
                from_node, to_node, params = self.parse_edge(edge_type)
                edges.append((edge_type, from_node, to_node, params))

            self.skip_newlines()

        return {
            "type": graph_type,
            "nodes": nodes,
            "edges": edges
        }

    def parse_node(self) -> Tuple[str, float, float]:
        self.expect(TokenType.NODE)
        node_id = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LPAREN)
        x = self.expect(TokenType.NUMBER).value
        self.expect(TokenType.COMMA)
        y = self.expect(TokenType.NUMBER).value
        self.expect(TokenType.RPAREN)
        return node_id, x, y

    def parse_edge(self, edge_type: TokenType) -> Tuple[str, str, dict]:
        self.expect(edge_type)
        from_node = self.expect(TokenType.IDENTIFIER).value
        to_node = self.expect(TokenType.IDENTIFIER).value

        params = {}
        while self.current_token().type == TokenType.IDENTIFIER:
            key = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.EQUALS)
            value = self.expect(TokenType.NUMBER).value
            params[key] = value

        return from_node, to_node, params

    def parse_simulation(self) -> List[dict]:
        self.skip_newlines()

        if self.current_token().type not in [TokenType.SIMULATION, TokenType.VEHICLES]:
            return []

        self.current_token()
        self.advance()
        self.expect(TokenType.COLON)
        self.skip_newlines()

        cars = []
        while self.current_token().type == TokenType.CAR:
            car_data = self.parse_car()
            cars.append(car_data)
            self.skip_newlines()

        return cars

    def parse_spawners_section(self) -> List[dict]:
        self.skip_newlines()
        if self.current_token().type != TokenType.SPAWNERS:
            return []

        self.expect(TokenType.SPAWNERS)
        self.expect(TokenType.COLON)
        self.skip_newlines()

        spawners = []
        while self.current_token().type == TokenType.SPAWNER:
            # Format: SPAWNER NodeID ratio=0.5
            self.expect(TokenType.SPAWNER)
            node_id = self.expect(TokenType.IDENTIFIER).value

            params = {}
            while self.current_token().type == TokenType.IDENTIFIER:
                key = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.EQUALS)
                value = self.expect(TokenType.NUMBER).value
                params[key] = value

            spawners.append({"node": node_id, "params": params})
            self.skip_newlines()

        return spawners

    def parse_car(self) -> dict:
        self.expect(TokenType.CAR)
        try:
            car_id = self.expect(TokenType.IDENTIFIER).value
        except SyntaxError:
            car_id = self.expect(TokenType.NUMBER).value

        self.expect(TokenType.LPAREN)
        start_node = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COMMA)
        end_node = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.RPAREN)

        return {
            "id": car_id,
            "start": start_node,
            "end": end_node
        }


def import_map(file_path: str):
    with open(file_path, "r") as f:
        content = f.read()

    tokenizer = Tokenizer(content)
    tokens = tokenizer.tokenize()

    parser = Parser(tokens)
    graph_data = parser.parse_graph()
    simulation_data = parser.parse_simulation()
    spawners_data = parser.parse_spawners_section()

    graph = build_graph(graph_data)
    vehicles = build_vehicles(simulation_data, graph)
    spawners = build_spawners(spawners_data, graph)

    return graph, vehicles, spawners


def build_graph(graph_data: dict) -> RoadGraph:
    graph = RoadGraph()
    graph_type = graph_data["type"]  # "cellular" ou "fluid"

    for node_id, (x, y) in graph_data["nodes"].items():
        graph.add_node(node_id, x, y)

    for edge_type, from_node, to_node, params in graph_data["edges"]:
        x1, y1 = graph_data["nodes"][from_node]
        x2, y2 = graph_data["nodes"][to_node]
        default_distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

        distance = float(params.get("distance", default_distance))
        vmax = int(params.get("vmax", 5))

        # Paramètres spécifiques
        prob_slow = float(params.get("prob_slow", 0.1))
        density_max = float(params.get("density_max", 0.2))  # Nouveau paramètre

        edge_obj = None
        edge_obj_back = None

        # --- SÉLECTION DU MODÈLE ---
        if graph_type == "cellular":
            if edge_type == TokenType.UEDGE:
                edge_obj = CellularEdge(distance=int(distance), vmax=vmax, prob_slow=prob_slow)
            elif edge_type == TokenType.BEDGE:
                edge_obj = CellularEdge(distance=int(distance), vmax=vmax, prob_slow=prob_slow)
                edge_obj_back = CellularEdge(distance=int(distance), vmax=vmax, prob_slow=prob_slow)

        elif graph_type == "fluid":
            if edge_type == TokenType.UEDGE:
                edge_obj = FluidEdge(distance=int(distance), vmax=vmax, density_max=density_max)
            elif edge_type == TokenType.BEDGE:
                edge_obj = FluidEdge(distance=int(distance), vmax=vmax, density_max=density_max)
                edge_obj_back = FluidEdge(distance=int(distance), vmax=vmax, density_max=density_max)

        else:
            raise SyntaxError(f"Unknown graph type: {graph_type}")

        # Ajout au graph
        if edge_obj:
            graph.add_edge(from_node, to_node, edge_obj)
        if edge_obj_back:
            graph.add_edge(to_node, from_node, edge_obj_back)

    return graph


def build_vehicles(simulation_data: List[dict], graph: RoadGraph) -> List[Tuple[Vehicle, any]]:
    vehicles = []
    path_func = CellularEdge.evaluate_weight

    for car_data in simulation_data:
        start_node = car_data["start"]
        end_node = car_data["end"]

        vehicle_path = graph.get_path(start_node, end_node, path_func)

        if not vehicle_path or len(vehicle_path) < 2:
            print(f"Warning: cannot find a path from {start_node} to {end_node} for the vehicle {car_data['id']}")
            continue

        vehicle = Vehicle(vehicle_id=car_data["id"], path=vehicle_path[1:])
        start_edge = graph.get_edge(vehicle_path[0], vehicle_path[1])
        vehicles.append((vehicle, start_edge))

    return vehicles


def build_spawners(spawners_data: List[dict], graph: RoadGraph) -> List[VehicleSpawner]:
    spawners = []
    for data in spawners_data:
        node_id = data["node"]
        if not graph.graph.has_node(node_id):
            print(f"Warning: Spawner defined on non-existent node '{node_id}'")
            continue

        ratio = float(data["params"].get("ratio", 0.05))

        spawners.append(VehicleSpawner(ratio, node_id))
    return spawners
