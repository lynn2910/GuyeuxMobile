"""
Rendering system for drawing roads, nodes, vehicles, and UI elements.
This module handles all visual output for the simulation.
OPTIMIZED VERSION with performance improvements.
"""

import pygame
import math
from typing import Tuple, Dict, Set, List
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

        # Cache pour les surfaces statiques
        self.static_surface = None
        self.static_zoom = None
        self.static_camera_pos = None
        self.needs_static_redraw = True

        # Cache pour les calculs de traffic lights
        self.traffic_light_cache = {}

    def invalidate_static_cache(self):
        """Force le redessin de la couche statique (routes et nœuds)"""
        self.needs_static_redraw = True

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
                key = tuple(sorted((src, dst)))
                self.bidirectional_edges.add(key)

    def is_bidirectional(self, src: str, dst: str) -> bool:
        """Checks if an edge is part of a bidirectional pair."""
        return tuple(sorted((src, dst))) in self.bidirectional_edges

    def draw_traffic_lights(self, graph, camera_convert_func, zoom: float, visible_nodes=None):
        """
        Draws indicators for traffic lights at intersections.
        OPTIMIZED: Cache les calculs de position. Nouveau style visuel.
        """
        # Ne dessiner les feux qu'à partir d'un certain zoom
        if zoom < 0.3:
            return

        # Tailles adaptatives
        light_size = max(3, min(8, int(4 * zoom)))

        for node_id, intersection in graph.intersections.items():
            if not hasattr(intersection, "get_state"):
                continue

            if visible_nodes is not None and node_id not in visible_nodes:
                continue

            node_data = graph.get_node(node_id)
            cx, cy = camera_convert_func((node_data['x'], node_data['y']))

            incoming_nodes = graph.get_incoming_nodes(node_id)
            num_incoming = len(incoming_nodes)

            if num_incoming == 0:
                continue

            # Disposition circulaire autour du nœud
            node_radius = max(10, min(35, Sizes.NODE_RADIUS_BASE * zoom * 0.6))
            light_distance = node_radius + light_size + 4

            angle_step = 2 * math.pi / num_incoming

            for i, inc_node in enumerate(incoming_nodes):
                state = intersection.get_state(inc_node)

                # Couleurs plus visibles
                if state == "GREEN":
                    color = (50, 255, 100)  # Vert vif
                    glow_color = (30, 200, 80)
                else:
                    color = (255, 50, 50)  # Rouge vif
                    glow_color = (200, 30, 30)

                # Position circulaire
                angle = i * angle_step - math.pi / 2  # Commencer en haut
                lx = cx + math.cos(angle) * light_distance
                ly = cy + math.sin(angle) * light_distance

                # Effet de glow si zoom suffisant
                if zoom > 0.6:
                    pygame.draw.circle(self.screen, glow_color, (int(lx), int(ly)), light_size + 2, 1)

                # Feu principal
                pygame.draw.circle(self.screen, (40, 40, 40), (int(lx), int(ly)), light_size + 1)
                pygame.draw.circle(self.screen, color, (int(lx), int(ly)), light_size)

    def draw_edge(self, src_pos: Tuple[float, float], dst_pos: Tuple[float, float],
                  edge, src: str, dst: str, is_hovered: bool, zoom: float):
        """
        Draws a single road edge and the traffic on it.
        OPTIMIZED: Amélioration du rendu à petite échelle.
        """
        base_width = Sizes.ROAD_WIDTH_BASE * zoom
        current_width = int(max(2, min(20, base_width)))

        # À petite échelle, simplifier le rendu
        if zoom < 0.3:
            current_width = max(1, int(current_width * 0.7))

        if is_hovered:
            current_width += 2

        start_draw, end_draw = src_pos, dst_pos
        if self.is_bidirectional(src, dst):
            # Réduire la séparation à petite échelle
            base_separation = Sizes.ROAD_SEPARATION if zoom >= 0.5 else Sizes.ROAD_SEPARATION * 0.6
            offset_dist = max(3, min(15, (base_separation / 2) * zoom))
            start_draw, end_draw = offset_line(src_pos, dst_pos, -offset_dist)

        color = self._get_traffic_color(edge)
        if is_hovered:
            color = Colors.ROAD_HOVER

        pygame.draw.line(self.screen, color, start_draw, end_draw, current_width)

        # Ne dessiner les flèches qu'à partir d'un certain zoom
        if zoom > 0.4:
            length = math.hypot(end_draw[0] - start_draw[0], end_draw[1] - start_draw[1])
            if length > 40:
                arrow_size = max(5, min(12, Sizes.ARROW_SIZE * zoom))
                arrow_points = get_arrow_points(start_draw, end_draw, arrow_size)
                pygame.draw.polygon(self.screen, Colors.TEXT_DIM, arrow_points)

        # Simplifier le rendu des véhicules à petite échelle
        if zoom > 0.25:
            if hasattr(edge, 'cells'):
                self._draw_cellular_vehicles(start_draw, end_draw, edge, zoom)
            elif hasattr(edge, 'get_vehicle_positions'):
                self._draw_fluid_traffic(start_draw, end_draw, edge, zoom)

    def _draw_cellular_vehicles(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float], edge, zoom: float):
        """
        Draws discrete vehicles for the cellular model.
        OPTIMIZED: Réduit le nombre de véhicules dessinés à petite échelle.
        """
        vehicle_radius = int(max(2, min(8, Sizes.VEHICLE_RADIUS * zoom)))
        dx_total = end_pos[0] - start_pos[0]
        dy_total = end_pos[1] - start_pos[1]

        # À petite échelle, ne dessiner qu'un véhicule sur N
        skip = 1
        if zoom < 0.5:
            skip = 3
        elif zoom < 1.0:
            skip = 2

        for i, vehicle in enumerate(edge.cells):
            if vehicle is not None and i % skip == 0:
                t_current = (i + 0.5) / edge.distance
                x = start_pos[0] + t_current * dx_total
                y = start_pos[1] + t_current * dy_total

                # Ne dessiner la traînée qu'à partir d'un certain zoom
                if vehicle.speed > 0 and zoom > 0.6:
                    prev_i = max(0, i - vehicle.speed)
                    t_prev = (prev_i + 0.5) / edge.distance
                    x_prev = start_pos[0] + t_prev * dx_total
                    y_prev = start_pos[1] + t_prev * dy_total
                    trail_color = (100, 150, 220)
                    trail_width = max(2, vehicle_radius)
                    pygame.draw.line(self.screen, trail_color, (int(x_prev), int(y_prev)), (int(x), int(y)),
                                     trail_width)

                color = Colors.VEHICLE if vehicle.speed > 0 else (200, 50, 50)
                pygame.draw.circle(self.screen, color, (int(x), int(y)), vehicle_radius)

    def _draw_fluid_traffic(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float], edge, zoom: float):
        """
        Draws continuous-position vehicles for the fluid model.
        OPTIMIZED: Limite le nombre de véhicules dessinés.
        """
        if not edge.vehicles:
            return

        vehicle_radius = int(max(2, min(6, Sizes.VEHICLE_RADIUS * zoom * 0.8)))

        # À petite échelle, limiter le nombre de véhicules affichés
        vehicles_to_draw = list(edge.get_vehicle_positions())  # Convertir en liste
        if zoom < 0.5 and len(vehicles_to_draw) > 20:
            vehicles_to_draw = vehicles_to_draw[::3]  # Afficher 1 véhicule sur 3

        for vehicle, ratio in vehicles_to_draw:
            x = start_pos[0] + ratio * (end_pos[0] - start_pos[0])
            y = start_pos[1] + ratio * (end_pos[1] - start_pos[1])
            pygame.draw.circle(self.screen, Colors.VEHICLE, (int(x), int(y)), vehicle_radius)

    def _get_traffic_color(self, edge) -> Tuple[int, int, int]:
        """Calculates an edge's color based on its normalized occupation."""
        occupation = edge.get_occupation_ratio()

        if occupation < 0.5:
            t = occupation / 0.5
            return lerp_color(Colors.TRAFFIC_LOW, Colors.TRAFFIC_MEDIUM, t)
        else:
            t = (occupation - 0.5) / 0.5
            return lerp_color(Colors.TRAFFIC_MEDIUM, Colors.TRAFFIC_HIGH, t)

    def draw_node(self, pos: Tuple[float, float], node_id: str, is_hovered: bool, zoom: float):
        """
        Draws a single intersection node.
        OPTIMIZED: Adapte le rendu au zoom avec tailles réduites.
        """
        # Ne pas dessiner les nœuds à très petite échelle
        if zoom < 0.15:
            return

        # Tailles réduites pour éviter la surcharge visuelle
        base_radius = Sizes.NODE_RADIUS_BASE * 0.6  # 40% plus petit
        scaled_radius = base_radius * zoom

        # Réduction supplémentaire à petite échelle
        if zoom < 0.5:
            scaled_radius *= 0.5
        elif zoom < 1.0:
            scaled_radius *= 0.7

        radius = int(max(3, min(20, scaled_radius)))  # Max réduit de 35 à 20

        if is_hovered:
            radius += 2

        outline_width = max(1, min(3, int(Sizes.NODE_OUTLINE_WIDTH * zoom)))
        x, y = int(pos[0]), int(pos[1])

        # Couleur gris foncé au lieu de blanc
        fill_color = Colors.NODE_HOVER if is_hovered else (80, 80, 80)

        # Dessiner avec antialiasing seulement si le zoom est suffisant
        if zoom > 0.5:
            pygame.draw.circle(self.screen, fill_color, (x, y), radius)
            pygame.draw.circle(self.screen, Colors.NODE_OUTLINE, (x, y), radius, outline_width)
        else:
            # Version simplifiée à petite échelle
            pygame.draw.circle(self.screen, fill_color, (x, y), radius)

        # Labels seulement à grand zoom
        if radius > 12 and zoom > 1.5:
            font = self.font_medium if radius > 18 else self.font_tiny
            text_surf = font.render(str(node_id), True, Colors.TEXT)
            text_rect = text_surf.get_rect(center=(x, y))
            self.screen.blit(text_surf, text_rect)

    def draw_info_box(self, pos: Tuple[int, int], lines: list, title: str = None):
        """Draws a semi-transparent box with information about a hovered object."""
        if not lines:
            return

        padding = Sizes.INFO_PADDING
        line_height = Sizes.INFO_LINE_HEIGHT

        rendered_lines = [self.font_medium.render(title, True, Colors.TEXT)] if title else []
        rendered_lines.extend([self.font_small.render(line, True, Colors.TEXT_DIM) for line in lines])

        max_w = max(surf.get_width() for surf in rendered_lines) if rendered_lines else 0
        box_w = max_w + padding * 2
        box_h = len(rendered_lines) * line_height + padding

        x, y = pos
        sw, sh = self.screen.get_size()
        if x + box_w > sw - 10:
            x = sw - box_w - 10
        if y + box_h > sh - 10:
            y = sh - box_h - 10

        bg_surface = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg_surface.fill(Colors.INFO_BG)
        pygame.draw.rect(bg_surface, Colors.INFO_BORDER, bg_surface.get_rect(), 1)
        self.screen.blit(bg_surface, (x, y))

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

        bg_surface = pygame.Surface((legend_w, legend_h), pygame.SRCALPHA)
        bg_surface.fill(Colors.INFO_BG)
        pygame.draw.rect(bg_surface, Colors.INFO_BORDER, bg_surface.get_rect(), 1)
        self.screen.blit(bg_surface, (legend_x, legend_y))

        self.screen.blit(self.font_small.render("Traffic Density", True, Colors.TEXT), (legend_x + 10, legend_y + 10))
        gradient_x, gradient_y = legend_x + 10, legend_y + 35
        gradient_h = 60
        for i in range(gradient_h):
            color = self._get_traffic_color_for_legend(i / gradient_h)
            pygame.draw.line(self.screen, color, (gradient_x, gradient_y + i), (gradient_x + 20, gradient_y + i))

        self.screen.blit(self.font_tiny.render("Low", True, Colors.TEXT_DIM), (gradient_x + 25, gradient_y))
        self.screen.blit(self.font_tiny.render("High", True, Colors.TEXT_DIM),
                         (gradient_x + 25, gradient_y + gradient_h - 10))

    def _get_traffic_color_for_legend(self, occupation: float) -> Tuple[int, int, int]:
        """Helper to get traffic color for a given ratio, matching the main logic."""
        if occupation < 0.5:
            return lerp_color(Colors.TRAFFIC_LOW, Colors.TRAFFIC_MEDIUM, occupation / 0.5)
        else:
            return lerp_color(Colors.TRAFFIC_MEDIUM, Colors.TRAFFIC_HIGH, (occupation - 0.5) / 0.5)
