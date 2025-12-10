"""
Rendering system for roads, nodes, and vehicles.
"""

import pygame
import math
from typing import Tuple, Optional
from ui.styles import Colors, Sizes, Fonts
from ui.geometry import (
    offset_line, get_arrow_points, lerp_color
)


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen

        # Use system fonts to avoid unicode/rectangle issues
        # 'Arial' is generally safe. None defaults to internal pygame font which handles numbers well but not symbols.
        self.font_large = pygame.font.SysFont("Arial", Fonts.LARGE, bold=True)
        self.font_medium = pygame.font.SysFont("Arial", Fonts.MEDIUM, bold=True)
        self.font_small = pygame.font.SysFont("Arial", Fonts.SMALL)
        self.font_tiny = pygame.font.SysFont("Arial", Fonts.TINY)

        self.bidirectional_edges = set()

    def clear(self):
        self.screen.fill(Colors.BG)

    def detect_bidirectional_edges(self, graph):
        """Identify edges that have a reverse counterpart to draw them side-by-side."""
        self.bidirectional_edges.clear()
        edges = list(graph.get_edges())
        existing_connections = set()

        for src, dst, _ in edges:
            existing_connections.add((src, dst))

        for src, dst, _ in edges:
            if (dst, src) in existing_connections:
                # Store tuple sorted so order doesn't matter for the key
                key = tuple(sorted((src, dst)))
                self.bidirectional_edges.add(key)

    def is_bidirectional(self, src: str, dst: str) -> bool:
        return tuple(sorted((src, dst))) in self.bidirectional_edges

    def draw_edge(self, src_pos: Tuple[float, float], dst_pos: Tuple[float, float],
                  edge, src: str, dst: str, is_hovered: bool, zoom: float):

        # --- CORRECTION DIMENSIONS ---
        # On limite (clamp) la largeur maximale de la route pour éviter l'effet "autoroute géante"
        base_width = Sizes.ROAD_WIDTH_BASE * zoom
        # Largeur : min 2px, max 20px (ajustable)
        current_width = int(max(2, min(20, base_width)))

        if is_hovered:
            current_width += 2

        # Gestion des doubles routes (offset)
        start_draw, end_draw = src_pos, dst_pos
        if self.is_bidirectional(src, dst):
            # L'écartement doit aussi être limité pour ne pas que les routes s'éloignent trop
            offset_dist = max(4, min(15, (Sizes.ROAD_SEPARATION / 2) * zoom))
            start_draw, end_draw = offset_line(src_pos, dst_pos, -offset_dist)

        # Dessin de la route
        color = self._get_traffic_color(edge)
        if is_hovered:
            color = Colors.ROAD_HOVER

        pygame.draw.line(self.screen, color, start_draw, end_draw, current_width)

        # Flèches
        dx = end_draw[0] - start_draw[0]
        dy = end_draw[1] - start_draw[1]
        length = math.hypot(dx, dy)

        # On ne dessine les flèches que si la route est assez longue visuellement
        if length > 40:
            # Taille flèche limitée aussi
            arrow_size = max(5, min(12, Sizes.ARROW_SIZE * zoom))
            arrow_points = get_arrow_points(start_draw, end_draw, arrow_size)
            arrow_color = Colors.TEXT_DIM
            pygame.draw.polygon(self.screen, arrow_color, arrow_points)

        self._draw_vehicles(start_draw, end_draw, edge, zoom)

    def _draw_vehicles(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float], edge, zoom: float):
        if not hasattr(edge, 'cells'):
            return

        vehicle_radius = int(max(3, min(8, int(Sizes.VEHICLE_RADIUS * zoom))))

        for i, cell in enumerate(edge.cells):
            if cell is not None:
                # Linear interpolation for position
                t = (i + 0.5) / edge.distance
                x = start_pos[0] + t * (end_pos[0] - start_pos[0])
                y = start_pos[1] + t * (end_pos[1] - start_pos[1])

                # Draw vehicle
                pygame.draw.circle(self.screen, Colors.VEHICLE, (int(x), int(y)), vehicle_radius)

    def _get_traffic_color(self, edge) -> Tuple[int, int, int]:
        if not hasattr(edge, 'cells'):
            return Colors.ROAD_BASE

        num_vehicles = sum(1 for cell in edge.cells if cell is not None)
        occupation = num_vehicles / max(edge.distance, 1)

        if occupation < 0.3:
            t = occupation / 0.3
            return lerp_color(Colors.TRAFFIC_LOW, Colors.TRAFFIC_MEDIUM, t)
        elif occupation < 0.8:
            t = (occupation - 0.3) / 0.5
            return lerp_color(Colors.TRAFFIC_MEDIUM, Colors.TRAFFIC_HIGH, t)
        else:
            return Colors.TRAFFIC_HIGH

    def draw_node(self, pos: Tuple[float, float], node_id: str,
                  is_hovered: bool, is_entrance: bool, zoom: float):

        # --- CORRECTION DIMENSIONS ---
        # C'est ici que ça bloquait : on limite le rayon entre 10 et 35 pixels
        # Peu importe le zoom, le cercle ne sera jamais plus gros que 35px
        scaled_radius = Sizes.NODE_RADIUS_BASE * zoom
        radius = int(max(10, min(35, scaled_radius)))

        if is_hovered:
            radius += 3

        outline_width = max(2, min(4, int(Sizes.NODE_OUTLINE_WIDTH * zoom)))

        x, y = int(pos[0]), int(pos[1])

        # Remplissage
        fill_color = Colors.NODE_HOVER if is_hovered else Colors.NODE_BASE
        pygame.draw.circle(self.screen, fill_color, (x, y), radius)

        # Contour
        outline_color = Colors.NODE_ENTRANCE if is_entrance else Colors.NODE_OUTLINE
        pygame.draw.circle(self.screen, outline_color, (x, y), radius, outline_width)

        # Texte (ID du node)
        # On affiche le texte seulement si le cercle est assez gros pour le contenir
        if radius > 15:
            # On adapte la police à la taille du cercle, sans dépasser MEDIUM
            if radius > 25:
                font = self.font_medium
            else:
                font = self.font_tiny

            text_surf = font.render(str(node_id), True, Colors.TEXT)  # True pour Anti-aliasing
            text_rect = text_surf.get_rect(center=(x, y))
            self.screen.blit(text_surf, text_rect)

    def draw_info_box(self, pos: Tuple[int, int], lines: list, title: str = None):
        """Draw a clean info box with shadow/border"""
        if not lines:
            return

        # Prepare Text Surfaces
        rendered_lines = []
        max_w = 0

        if title:
            t_surf = self.font_medium.render(title, True, Colors.TEXT)
            rendered_lines.append(t_surf)
            max_w = max(max_w, t_surf.get_width())

        for line in lines:
            l_surf = self.font_small.render(line, True, Colors.TEXT_DIM)
            rendered_lines.append(l_surf)
            max_w = max(max_w, l_surf.get_width())

        # Layout
        padding = Sizes.INFO_PADDING
        line_height = Sizes.INFO_LINE_HEIGHT
        box_w = max_w + padding * 2
        box_h = len(rendered_lines) * line_height + padding * 2

        # Clamp to screen
        x, y = pos
        sw, sh = self.screen.get_size()
        if x + box_w > sw: x -= box_w + 10
        if y + box_h > sh: y -= box_h + 10

        # Background
        s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        s.fill(Colors.INFO_BG)
        pygame.draw.rect(s, Colors.INFO_BORDER, s.get_rect(), 1)

        self.screen.blit(s, (x, y))

        # Draw Text
        curr_y = y + padding
        for i, surf in enumerate(rendered_lines):
            self.screen.blit(surf, (x + padding, curr_y))
            curr_y += line_height

    def draw_tick_counter(self, tick: int):
        text = f"Tick: {tick}"
        surf = self.font_medium.render(text, True, Colors.TEXT)
        self.screen.blit(surf, (20, 20))

    def draw_controls_help(self):
        help_text = [
            "L-Click + Drag: Pan",
            "Wheel: Zoom",
            "R: Reset"
        ]

        y = 50
        for line in help_text:
            surf = self.font_tiny.render(line, True, Colors.TEXT_DIM)
            self.screen.blit(surf, (20, y))
            y += 15
