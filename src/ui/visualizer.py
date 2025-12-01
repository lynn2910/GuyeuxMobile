import pygame
import math
from typing import Optional, Tuple


class Visualizer:
    def __init__(self, graph, width: int = 1200, height: int = 800):
        """
        Initialize the visualizer
        :param graph: The RoadGraph, with nodes and edges
        :param width: Window width
        :param height: Window height
        """
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Traffic Simulation")

        self.graph = graph
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

        # Colors
        self.BG_COLOR = (240, 240, 240)
        self.NODE_COLOR = (70, 130, 180)
        self.NODE_HOVER_COLOR = (100, 160, 210)
        self.EDGE_COLOR = (100, 100, 100)
        self.EDGE_HOVER_COLOR = (255, 140, 0)
        self.VEHICLE_COLOR = (220, 20, 60)
        self.TEXT_COLOR = (0, 0, 0)
        self.INFO_BG_COLOR = (255, 255, 255)
        self.INFO_BORDER_COLOR = (0, 0, 0)

        # UI State
        self.hovered_node = None
        self.hovered_edge = None
        self.current_tick = 0

        # Normalized coordinates
        self._compute_normalized_positions()

        self.clock = pygame.time.Clock()
        self.running = True

    def _compute_normalized_positions(self):
        """
        Convert graph coordinates to screen coordinates, with margin
        """
        nodes = list(self.graph.graph.nodes(data=True))

        if not nodes:
            return

        min_x = min(data['x'] for _, data in nodes)
        max_x = max(data['x'] for _, data in nodes)
        min_y = min(data['y'] for _, data in nodes)
        max_y = max(data['y'] for _, data in nodes)

        margin = 80
        usable_width = self.width - 2 * margin
        usable_height = self.height - 2 * margin - 60

        # Normaliser
        range_x = max_x - min_x if max_x != min_x else 1
        range_y = max_y - min_y if max_y != min_y else 1

        self.node_positions = {}
        for node_id, data in nodes:
            norm_x = (data['x'] - min_x) / range_x
            norm_y = (data['y'] - min_y) / range_y

            screen_x = margin + norm_x * usable_width
            screen_y = margin + (1 - norm_y) * usable_height

            self.node_positions[node_id] = (int(screen_x), int(screen_y))

    @staticmethod
    def _get_mouse_pos() -> Tuple[int, int]:
        """Return the mouse position"""
        return pygame.mouse.get_pos()

    def _check_node_hover(self, mouse_pos: Tuple[int, int]) -> Optional[str]:
        """
        Verify if the mouse is hovering a node
        :param mouse_pos: Mouse position
        :return: Node ID or None
        """
        node_radius = 15
        for node_id, (x, y) in self.node_positions.items():
            dist = math.sqrt((mouse_pos[0] - x) ** 2 + (mouse_pos[1] - y) ** 2)
            if dist <= node_radius:
                return node_id
        return None

    def _check_edge_hover(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[str, str, dict]]:
        """
        Verify if the mouse is hovering an edge
        :param mouse_pos: Mouse position
        :return: (src, dst, data) of the hovered edge, or None
        """
        threshold = 10

        for src, dst, data in self.graph.get_edges():
            src_pos = self.node_positions[src]
            dst_pos = self.node_positions[dst]

            dist = self._point_to_line_distance(mouse_pos, src_pos, dst_pos)

            if dist <= threshold and self._is_between_nodes(mouse_pos, src_pos, dst_pos):
                return src, dst, data

        return None

    @staticmethod
    def _point_to_line_distance(point, line_start, line_end) -> float:
        """Calculate distance from a point to a line"""
        px, py = point
        x1, y1 = line_start
        x2, y2 = line_end

        line_length_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
        if line_length_sq == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_length_sq))
        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)

        return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)

    def _is_between_nodes(self, point, node1, node2, margin=20) -> bool:
        """Verify if a point is between two other nodes"""
        px, py = point
        x1, y1 = node1
        x2, y2 = node2

        min_x, max_x = min(x1, x2) - margin, max(x1, x2) + margin
        min_y, max_y = min(y1, y2) - margin, max(y1, y2) + margin

        return min_x <= px <= max_x and min_y <= py <= max_y

    def update(self, current_tick: int):
        """
        Update the ui
        :param current_tick: The current tick
        """
        self.current_tick = current_tick
        mouse_pos = self._get_mouse_pos()

        self.hovered_node = self._check_node_hover(mouse_pos)
        if not self.hovered_node:
            self.hovered_edge = self._check_edge_hover(mouse_pos)
        else:
            self.hovered_edge = None

        self.screen.fill(self.BG_COLOR)
        self._draw_edges()
        self._draw_nodes()
        self._draw_tick_info()
        self._draw_hover_info(mouse_pos)

        pygame.display.flip()

    def _draw_edges(self):
        """Draw all edges with their respective traffics"""
        for src, dst, data in self.graph.get_edges():
            edge = data['object']
            src_pos = self.node_positions[src]
            dst_pos = self.node_positions[dst]

            is_hovered = (self.hovered_edge and
                          self.hovered_edge[0] == src and
                          self.hovered_edge[1] == dst)

            color = self.EDGE_HOVER_COLOR if is_hovered else self.EDGE_COLOR
            width = 4 if is_hovered else 2

            pygame.draw.line(self.screen, color, src_pos, dst_pos, width)

            self._draw_arrow(src_pos, dst_pos, color)

            edge.draw_edge(src_pos, dst_pos, self.screen, self.VEHICLE_COLOR)

    def _draw_arrow(self, start, end, color):
        """Draw an arrow in the middle of the edge"""
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2

        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        arrow_size = 10

        # Points de la flèche
        arrow_points = [
            (mid_x, mid_y),
            (mid_x - arrow_size * math.cos(angle - math.pi / 6),
             mid_y - arrow_size * math.sin(angle - math.pi / 6)),
            (mid_x - arrow_size * math.cos(angle + math.pi / 6),
             mid_y - arrow_size * math.sin(angle + math.pi / 6))
        ]

        pygame.draw.polygon(self.screen, color, arrow_points)

    def _draw_nodes(self):
        """Draw all nodes"""
        node_radius = 15

        for node_id, (x, y) in self.node_positions.items():
            is_hovered = (node_id == self.hovered_node)
            color = self.NODE_HOVER_COLOR if is_hovered else self.NODE_COLOR

            pygame.draw.circle(self.screen, color, (x, y), node_radius)
            pygame.draw.circle(self.screen, self.TEXT_COLOR, (x, y), node_radius, 2)

            # Label du nœud
            label = self.font_small.render(node_id, True, self.TEXT_COLOR)
            label_rect = label.get_rect(center=(x, y - node_radius - 12))
            self.screen.blit(label, label_rect)

    def _draw_tick_info(self):
        """Draw tick information"""
        tick_text = f"Tick: {self.current_tick}"
        text_surface = self.font.render(tick_text, True, self.TEXT_COLOR)

        padding = 10
        rect = text_surface.get_rect(topleft=(10, 10))
        bg_rect = rect.inflate(padding * 2, padding * 2)
        pygame.draw.rect(self.screen, self.INFO_BG_COLOR, bg_rect)
        pygame.draw.rect(self.screen, self.INFO_BORDER_COLOR, bg_rect, 2)

        self.screen.blit(text_surface, rect)

    def _draw_hover_info(self, mouse_pos: Tuple[int, int]):
        """Draw information when hovering"""
        if self.hovered_node:
            self._draw_node_info(mouse_pos, self.hovered_node)
        elif self.hovered_edge:
            self._draw_edge_info(mouse_pos, self.hovered_edge)

    def _draw_node_info(self, mouse_pos: Tuple[int, int], node_id: str):
        """Draw node details"""
        lines = [f"Node: {node_id}"]
        self._draw_info_box(mouse_pos, lines)

    def _draw_edge_info(self, mouse_pos: Tuple[int, int], edge_data):
        """Draw edge details"""
        src, dst, data = edge_data
        edge = data['object']

        lines = [
            f"Edge: {src} → {dst}",
            f"Distance: {edge.distance}"
        ]

        if hasattr(edge, 'get_infos'):
            lines.extend(edge.get_infos())

        self._draw_info_box(mouse_pos, lines)

    def _draw_info_box(self, mouse_pos: Tuple[int, int], lines: list):
        """Draw details box"""
        padding = 8
        line_height = 22

        max_width = max(self.font_small.size(line)[0] for line in lines)
        box_width = max_width + padding * 2
        box_height = len(lines) * line_height + padding * 2

        box_x = mouse_pos[0] + 15
        box_y = mouse_pos[1] + 15

        if box_x + box_width > self.width:
            box_x = mouse_pos[0] - box_width - 15
        if box_y + box_height > self.height:
            box_y = mouse_pos[1] - box_height - 15

        box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(self.screen, self.INFO_BG_COLOR, box_rect)
        pygame.draw.rect(self.screen, self.INFO_BORDER_COLOR, box_rect, 2)

        for i, line in enumerate(lines):
            text_surface = self.font_small.render(line, True, self.TEXT_COLOR)
            self.screen.blit(text_surface, (box_x + padding, box_y + padding + i * line_height))

    def handle_events(self):
        """Manage pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return False

        return True

    @staticmethod
    def close():
        """Close pygame gracefully"""
        pygame.quit()
