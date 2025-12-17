"""
Rendering system for drawing roads, nodes, vehicles, and UI elements.
This module handles all visual output for the simulation.
"""

import pygame
import math
from typing import Tuple
from ui.styles import Colors, Sizes, Fonts
from ui.geometry import offset_line, get_arrow_points, lerp_color


class Renderer:
    """
    Manages all drawing operations for the simulation, including the graph,
    vehicles, and user interface overlays.
    """
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        pygame.font.init()
        self.font_large = pygame.font.SysFont("Arial", Fonts.LARGE, bold=True)
        self.font_medium = pygame.font.SysFont("Arial", Fonts.MEDIUM, bold=True)
        self.font_small = pygame.font.SysFont("Arial", Fonts.SMALL)
        self.font_tiny = pygame.font.SysFont("Arial", Fonts.TINY)
        self.bidirectional_edges = set()

    def clear(self):
        """Fills the screen with the background color."""
        self.screen.fill(Colors.BG)

    def detect_bidirectional_edges(self, graph):
        """
        Pre-processes the graph to identify edges that have a counterpart in the
        opposite direction. This allows them to be drawn side-by-side.
        """
        self.bidirectional_edges.clear()
        edges = list(graph.get_edges())
        existing_connections = {(src, dst) for src, dst, _ in edges}

        for src, dst, _ in edges:
            if (dst, src) in existing_connections:
                # Store a canonical representation of the bidirectional edge pair.
                key = tuple(sorted((src, dst)))
                self.bidirectional_edges.add(key)

    def is_bidirectional(self, src: str, dst: str) -> bool:
        """Checks if an edge is part of a bidirectional pair."""
        return tuple(sorted((src, dst))) in self.bidirectional_edges

    def draw_traffic_lights(self, graph, camera_convert_func, zoom: float):
        """
        Draws indicators for traffic lights at intersections.
        The positions are calculated in screen space to ensure they align
        correctly with the rendered nodes and edges, regardless of zoom.
        """
        # Define visual sizes based on zoom level, clamped to a min/max range.
        node_radius_visual = max(10, min(35, Sizes.NODE_RADIUS_BASE * zoom))
        road_width_visual = max(2, min(20, Sizes.ROAD_WIDTH_BASE * zoom))
        light_radius = max(4, int(Sizes.TRAFFIC_LIGHT_RADIUS * zoom))

        # Define offsets in screen pixels for consistent placement.
        offset_back_px = node_radius_visual + 5  # Distance from node center
        offset_side_px = (road_width_visual / 2) + light_radius + 2  # Distance from edge centerline

        for node_id, intersection in graph.intersections.items():
            if not hasattr(intersection, "get_state"):
                continue

            # Get the screen coordinates of the intersection's center.
            node_data = graph.get_node(node_id)
            cx, cy = camera_convert_func((node_data['x'], node_data['y']))

            for inc_node in graph.get_incoming_nodes(node_id):
                state = intersection.get_state(inc_node)
                color = Colors.TL_GREEN if state == "GREEN" else Colors.TL_RED

                # Get the screen coordinates of the incoming node.
                inc_data = graph.get_node(inc_node)
                ix, iy = camera_convert_func((inc_data['x'], inc_data['y']))

                # Vector from the intersection center towards the incoming node.
                vx, vy = ix - cx, iy - cy
                dist = math.hypot(vx, vy)
                if dist < 1: continue

                # Normalized direction vector (pointing away from the intersection).
                ux, uy = vx / dist, vy / dist
                # Perpendicular vector to find the right side of the incoming lane.
                px, py = -uy, ux

                # Final light position calculation in screen space.
                lx = cx + (ux * offset_back_px) + (px * offset_side_px)
                ly = cy + (uy * offset_back_px) + (py * offset_side_px)

                pygame.draw.circle(self.screen, Colors.TL_OUTLINE, (int(lx), int(ly)), light_radius + 1)
                pygame.draw.circle(self.screen, color, (int(lx), int(ly)), light_radius)

    def draw_edge(self, src_pos: Tuple[float, float], dst_pos: Tuple[float, float],
                  edge, src: str, dst: str, is_hovered: bool, zoom: float):
        """Draws a single road edge and the traffic on it."""
        base_width = Sizes.ROAD_WIDTH_BASE * zoom
        current_width = int(max(2, min(20, base_width)))
        if is_hovered:
            current_width += 2

        # Offset the line if it's part of a two-way road.
        start_draw, end_draw = src_pos, dst_pos
        if self.is_bidirectional(src, dst):
            offset_dist = max(4, min(15, (Sizes.ROAD_SEPARATION / 2) * zoom))
            start_draw, end_draw = offset_line(src_pos, dst_pos, -offset_dist)

        # Draw the road itself, colored by traffic density.
        color = self._get_traffic_color(edge)
        if is_hovered:
            color = Colors.ROAD_HOVER
        pygame.draw.line(self.screen, color, start_draw, end_draw, current_width)

        # Draw direction arrows if the edge is long enough.
        length = math.hypot(end_draw[0] - start_draw[0], end_draw[1] - start_draw[1])
        if length > 40:
            arrow_size = max(5, min(12, Sizes.ARROW_SIZE * zoom))
            arrow_points = get_arrow_points(start_draw, end_draw, arrow_size)
            pygame.draw.polygon(self.screen, Colors.TEXT_DIM, arrow_points)

        # Delegate vehicle drawing to the appropriate method based on the edge model.
        if hasattr(edge, 'cells'):
            self._draw_cellular_vehicles(start_draw, end_draw, edge, zoom)
        elif hasattr(edge, 'get_vehicle_positions'):
            self._draw_fluid_traffic(start_draw, end_draw, edge, zoom)

    def _draw_cellular_vehicles(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float], edge, zoom: float):
        """Draws discrete vehicles for the cellular model, with a motion trail effect."""
        vehicle_radius = int(max(3, min(8, Sizes.VEHICLE_RADIUS * zoom)))
        dx_total = end_pos[0] - start_pos[0]
        dy_total = end_pos[1] - start_pos[1]

        for i, vehicle in enumerate(edge.cells):
            if vehicle is not None:
                # Current position at the center of the cell.
                t_current = (i + 0.5) / edge.distance
                x = start_pos[0] + t_current * dx_total
                y = start_pos[1] + t_current * dy_total

                # Draw a trail behind the vehicle to indicate motion.
                if vehicle.speed > 0:
                    prev_i = max(0, i - vehicle.speed)
                    t_prev = (prev_i + 0.5) / edge.distance
                    x_prev = start_pos[0] + t_prev * dx_total
                    y_prev = start_pos[1] + t_prev * dy_total
                    trail_color = (100, 150, 220)
                    trail_width = max(2, vehicle_radius)
                    pygame.draw.line(self.screen, trail_color, (int(x_prev), int(y_prev)), (int(x), int(y)), trail_width)

                # Draw the vehicle itself. Color it red if it's stopped.
                color = Colors.VEHICLE if vehicle.speed > 0 else (200, 50, 50)
                pygame.draw.circle(self.screen, color, (int(x), int(y)), vehicle_radius)

    def _draw_fluid_traffic(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float], edge, zoom: float):
        """Draws continuous-position vehicles for the fluid model."""
        if not edge.vehicles:
            return
        vehicle_radius = int(max(2, min(6, Sizes.VEHICLE_RADIUS * zoom * 0.8)))

        for vehicle, ratio in edge.get_vehicle_positions():
            # Interpolate vehicle position along the edge.
            x = start_pos[0] + ratio * (end_pos[0] - start_pos[0])
            y = start_pos[1] + ratio * (end_pos[1] - start_pos[1])
            pygame.draw.circle(self.screen, Colors.VEHICLE, (int(x), int(y)), vehicle_radius)

    def _get_traffic_color(self, edge) -> Tuple[int, int, int]:
        """Calculates an edge's color based on its normalized occupation."""
        occupation = edge.get_occupation_ratio()

        # Interpolate between green, yellow, and red based on occupation level.
        if occupation < 0.5:
            t = occupation / 0.5
            return lerp_color(Colors.TRAFFIC_LOW, Colors.TRAFFIC_MEDIUM, t)
        else:
            t = (occupation - 0.5) / 0.5
            return lerp_color(Colors.TRAFFIC_MEDIUM, Colors.TRAFFIC_HIGH, t)

    def draw_node(self, pos: Tuple[float, float], node_id: str, is_hovered: bool, zoom: float):
        """Draws a single intersection node."""
        scaled_radius = Sizes.NODE_RADIUS_BASE * zoom
        radius = int(max(10, min(35, scaled_radius)))
        if is_hovered:
            radius += 3
        outline_width = max(2, min(4, int(Sizes.NODE_OUTLINE_WIDTH * zoom)))
        x, y = int(pos[0]), int(pos[1])

        # Draw fill and outline.
        fill_color = Colors.NODE_HOVER if is_hovered else Colors.NODE_BASE
        pygame.draw.circle(self.screen, fill_color, (x, y), radius)
        pygame.draw.circle(self.screen, Colors.NODE_OUTLINE, (x, y), radius, outline_width)

        # Draw the node's ID if zoomed in enough.
        if radius > 15:
            font = self.font_medium if radius > 25 else self.font_tiny
            text_surf = font.render(str(node_id), True, Colors.TEXT)
            text_rect = text_surf.get_rect(center=(x, y))
            self.screen.blit(text_surf, text_rect)

    def draw_info_box(self, pos: Tuple[int, int], lines: list, title: str = None):
        """Draws a semi-transparent box with information about a hovered object."""
        if not lines: return
        padding = Sizes.INFO_PADDING
        line_height = Sizes.INFO_LINE_HEIGHT

        # Render text surfaces and calculate box size.
        rendered_lines = [self.font_medium.render(title, True, Colors.TEXT)] if title else []
        rendered_lines.extend([self.font_small.render(line, True, Colors.TEXT_DIM) for line in lines])
        max_w = max(surf.get_width() for surf in rendered_lines) if rendered_lines else 0
        box_w = max_w + padding * 2
        box_h = len(rendered_lines) * line_height + padding
        
        # Position box, ensuring it stays on screen.
        x, y = pos
        sw, sh = self.screen.get_size()
        if x + box_w > sw - 10: x = sw - box_w - 10
        if y + box_h > sh - 10: y = sh - box_h - 10

        # Draw background and border.
        bg_surface = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg_surface.fill(Colors.INFO_BG)
        pygame.draw.rect(bg_surface, Colors.INFO_BORDER, bg_surface.get_rect(), 1)
        self.screen.blit(bg_surface, (x, y))

        # Draw text lines.
        for i, surf in enumerate(rendered_lines):
            self.screen.blit(surf, (x + padding, y + (padding / 2) + i * line_height))

    def draw_tick_counter(self, tick: int):
        """Displays the current simulation tick."""
        text = f"Tick: {tick}"
        surf = self.font_medium.render(text, True, Colors.TEXT)
        self.screen.blit(surf, (20, 20))

    def draw_controls_help(self):
        """Displays help text for camera controls."""
        help_text = ["L-Click + Drag: Pan", "Wheel: Zoom", "R: Reset View"]
        y = 50
        for line in help_text:
            surf = self.font_tiny.render(line, True, Colors.TEXT_DIM)
            self.screen.blit(surf, (20, y))
            y += 15

    def draw_legend(self, screen_width: int, screen_height: int):
        """Draws a legend for the traffic density colors."""
        legend_x, legend_y = screen_width - 150, 20
        legend_w, legend_h = 130, 110

        # Draw background.
        bg_surface = pygame.Surface((legend_w, legend_h), pygame.SRCALPHA)
        bg_surface.fill(Colors.INFO_BG)
        pygame.draw.rect(bg_surface, Colors.INFO_BORDER, bg_surface.get_rect(), 1)
        self.screen.blit(bg_surface, (legend_x, legend_y))

        # Draw title and color gradient.
        self.screen.blit(self.font_small.render("Traffic Density", True, Colors.TEXT), (legend_x + 10, legend_y + 10))
        gradient_x, gradient_y = legend_x + 10, legend_y + 35
        gradient_h = 60
        for i in range(gradient_h):
            color = self._get_traffic_color_for_legend(i / gradient_h)
            pygame.draw.line(self.screen, color, (gradient_x, gradient_y + i), (gradient_x + 20, gradient_y + i))

        # Draw labels.
        self.screen.blit(self.font_tiny.render("Low", True, Colors.TEXT_DIM), (gradient_x + 25, gradient_y))
        self.screen.blit(self.font_tiny.render("High", True, Colors.TEXT_DIM), (gradient_x + 25, gradient_y + gradient_h - 10))

    def _get_traffic_color_for_legend(self, occupation: float) -> Tuple[int, int, int]:
        """Helper to get traffic color for a given ratio, matching the main logic."""
        if occupation < 0.5:
            return lerp_color(Colors.TRAFFIC_LOW, Colors.TRAFFIC_MEDIUM, occupation / 0.5)
        else:
            return lerp_color(Colors.TRAFFIC_MEDIUM, Colors.TRAFFIC_HIGH, (occupation - 0.5) / 0.5)
