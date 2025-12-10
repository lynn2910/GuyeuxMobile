"""
Rendering system for roads, nodes, and vehicles.
"""

import pygame
import math
from typing import Tuple, Optional, Dict
from ui.styles import Colors, Sizes, Fonts
from ui.geometry import (
    offset_line, get_arrow_points, interpolate_points,
    is_point_near_segment, lerp_color
)


class Renderer:
    """
    Handles all rendering operations for the visualization.
    """

    def __init__(self, screen: pygame.Surface):
        """
        Initialize renderer.

        :param screen: Pygame surface to draw on
        """
        self.screen = screen

        # Fonts
        self.font_large = pygame.font.Font(None, Fonts.LARGE)
        self.font_medium = pygame.font.Font(None, Fonts.MEDIUM)
        self.font_small = pygame.font.Font(None, Fonts.SMALL)
        self.font_tiny = pygame.font.Font(None, Fonts.TINY)

        # Cache for bidirectional edge detection
        self.bidirectional_edges = set()

    def clear(self):
        """Clear the screen"""
        self.screen.fill(Colors.BG)

    def detect_bidirectional_edges(self, graph):
        """
        Detect which edges are bidirectional.

        :param graph: RoadGraph instance
        """
        self.bidirectional_edges.clear()

        edges = list(graph.get_edges())
        edge_pairs = set()

        for src, dst, _ in edges:
            edge_pairs.add((src, dst))

        # Check for reverse edges
        for src, dst, _ in edges:
            if (dst, src) in edge_pairs:
                # This is a bidirectional edge
                self.bidirectional_edges.add((min(src, dst), max(src, dst)))

    def is_bidirectional(self, src: str, dst: str) -> bool:
        """Check if an edge is bidirectional"""
        return (min(src, dst), max(src, dst)) in self.bidirectional_edges

    def draw_edge(self, src_pos: Tuple[float, float], dst_pos: Tuple[float, float],
                  edge, src: str, dst: str, is_hovered: bool = False):
        """
        Draw a single road edge with traffic.

        :param src_pos: Source node position (world coordinates)
        :param dst_pos: Destination node position (world coordinates)
        :param edge: Edge object containing traffic data
        :param src: Source node ID
        :param dst: Destination node ID
        :param is_hovered: Whether this edge is hovered
        """
        # Check if this is part of a bidirectional pair
        is_bidir = self.is_bidirectional(src, dst)

        # Calculate offset for bidirectional roads
        offset = 0
        if is_bidir:
            # Determine which direction this edge goes
            if src < dst:
                offset = Sizes.ROAD_SEPARATION / 2
            else:
                offset = -Sizes.ROAD_SEPARATION / 2

        # Apply offset
        if offset != 0:
            render_start, render_end = offset_line(src_pos, dst_pos, offset)
        else:
            render_start, render_end = src_pos, dst_pos

        # Calculate traffic density color
        color = self._get_traffic_color(edge)

        # Draw road outline (darker)
        width = Sizes.ROAD_WIDTH_HOVER if is_hovered else Sizes.ROAD_WIDTH_BASE
        pygame.draw.line(
            self.screen, Colors.ROAD_OUTLINE,
            render_start, render_end,
            width + Sizes.ROAD_OUTLINE_WIDTH * 2
        )

        # Draw road main line
        road_color = Colors.ROAD_HOVER if is_hovered else color
        pygame.draw.line(
            self.screen, road_color,
            render_start, render_end,
            width
        )

        # Draw direction arrow
        arrow_points = get_arrow_points(render_start, render_end, Sizes.ARROW_SIZE)
        pygame.draw.polygon(self.screen, Colors.TEXT if is_hovered else Colors.TEXT_DIM, arrow_points)

        # Draw vehicles
        edge.draw_edge(render_start, render_end, self.screen, Colors.VEHICLE)

    def _get_traffic_color(self, edge) -> Tuple[int, int, int]:
        """
        Calculate road color based on traffic density.

        :param edge: Edge object
        :return: RGB color tuple
        """
        if not hasattr(edge, 'cells'):
            return Colors.ROAD_BASE

        # Calculate occupation rate
        num_vehicles = sum(1 for cell in edge.cells if cell is not None)
        occupation = num_vehicles / max(edge.distance, 1)

        # Interpolate between colors based on occupation
        if occupation < 0.3:
            # Low traffic: green to yellow
            t = occupation / 0.3
            return lerp_color(Colors.TRAFFIC_LOW, Colors.TRAFFIC_MEDIUM, t)
        elif occupation < 0.7:
            # Medium traffic: yellow to red
            t = (occupation - 0.3) / 0.4
            return lerp_color(Colors.TRAFFIC_MEDIUM, Colors.TRAFFIC_HIGH, t)
        else:
            # High traffic: red
            return Colors.TRAFFIC_HIGH

    def draw_node(self, pos: Tuple[float, float], node_id: str,
                  is_hovered: bool = False, is_entrance: bool = False):
        """
        Draw a single node.

        :param pos: Node position (screen coordinates)
        :param node_id: Node identifier
        :param is_hovered: Whether this node is hovered
        :param is_entrance: Whether this is an entrance node
        """
        radius = Sizes.NODE_RADIUS_HOVER if is_hovered else Sizes.NODE_RADIUS

        # Choose color
        if is_entrance:
            color = Colors.NODE_ENTRANCE
            outline = Colors.NODE_ENTRANCE
        else:
            color = Colors.NODE_HOVER if is_hovered else Colors.NODE_BASE
            outline = Colors.NODE_OUTLINE

        # Draw node circle
        pygame.draw.circle(self.screen, color, pos, radius)
        pygame.draw.circle(self.screen, outline, pos, radius, Sizes.NODE_OUTLINE_WIDTH)

        # Draw label
        label = self.font_tiny.render(node_id, True, Colors.TEXT)
        label_rect = label.get_rect(center=(pos[0], pos[1] - radius - 12))
        self.screen.blit(label, label_rect)

    def draw_info_box(self, pos: Tuple[int, int], lines: list, title: str = None):
        """
        Draw an information box at the specified position.

        :param pos: Position (screen coordinates)
        :param lines: List of text lines to display
        :param title: Optional title for the box
        """
        if not lines:
            return

        # Calculate box dimensions
        padding = Sizes.INFO_PADDING
        line_height = Sizes.INFO_LINE_HEIGHT

        all_lines = [title] + lines if title else lines
        max_width = max(self.font_small.size(line)[0] for line in all_lines)
        box_width = max_width + padding * 2
        box_height = len(all_lines) * line_height + padding * 2

        # Position box (avoid screen edges)
        box_x, box_y = pos
        screen_w, screen_h = self.screen.get_size()

        if box_x + box_width > screen_w:
            box_x = pos[0] - box_width - 15
        if box_y + box_height > screen_h:
            box_y = pos[1] - box_height - 15

        # Create semi-transparent surface
        box_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        box_surface.fill(Colors.INFO_BG)

        # Draw border
        pygame.draw.rect(box_surface, Colors.INFO_BORDER,
                         box_surface.get_rect(), 2)

        # Draw text
        for i, line in enumerate(all_lines):
            if i == 0 and title:
                # Title in bold/larger
                text = self.font_medium.render(line, True, Colors.TEXT)
            else:
                text = self.font_small.render(line, True, Colors.TEXT_DIM if i > 0 else Colors.TEXT)
            box_surface.blit(text, (padding, padding + i * line_height))

        # Blit to screen
        self.screen.blit(box_surface, (box_x, box_y))

    def draw_tick_counter(self, tick: int):
        """
        Draw the current tick counter.

        :param tick: Current simulation tick
        """
        text = f"Tick: {tick}"
        text_surface = self.font_medium.render(text, True, Colors.TEXT)

        padding = Sizes.INFO_PADDING
        rect = text_surface.get_rect(topleft=(10, 10))
        bg_rect = rect.inflate(padding * 2, padding * 2)

        # Semi-transparent background
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill(Colors.INFO_BG)
        pygame.draw.rect(bg_surface, Colors.INFO_BORDER, bg_surface.get_rect(), 2)

        self.screen.blit(bg_surface, bg_rect.topleft)
        self.screen.blit(text_surface, rect)

    def draw_controls_help(self):
        """Draw keyboard/mouse controls help"""
        lines = [
            "Controls:",
            "  Mouse Wheel: Zoom",
            "  Middle Click + Drag: Pan",
            "  R: Reset View",
            "  ESC: Quit"
        ]

        y_offset = 60
        for line in lines:
            text = self.font_tiny.render(line, True, Colors.TEXT_DIM)
            self.screen.blit(text, (10, y_offset))
            y_offset += 18
