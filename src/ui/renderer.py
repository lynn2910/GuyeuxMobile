"""
Rendering system for roads, nodes, and vehicles with improved fluid visualization.
"""

import pygame
import math
from typing import Tuple, Optional
from ui.styles import Colors, Sizes, Fonts
from ui.geometry import offset_line, get_arrow_points, lerp_color


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen

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
                key = tuple(sorted((src, dst)))
                self.bidirectional_edges.add(key)

    def is_bidirectional(self, src: str, dst: str) -> bool:
        return tuple(sorted((src, dst))) in self.bidirectional_edges

    def draw_traffic_lights(self, graph, camera_convert_func, zoom: float):
        """
        Dessine les indicateurs de feux tricolores.
        CORRIGÉ : Calcul en espace écran pour coller parfaitement aux nœuds clippés.
        """
        # 1. Récupérer les tailles VISUELLES exactes (les mêmes que dans draw_node/draw_edge)
        # Rayon du noeud tel qu'il est dessiné (borné entre 10 et 35 pixels)
        node_radius_visual = max(10, min(35, Sizes.NODE_RADIUS_BASE * zoom))

        # Largeur de la route telle qu'elle est dessinée (bornée entre 2 et 20 pixels)
        road_width_visual = max(2, min(20, Sizes.ROAD_WIDTH_BASE * zoom))

        # Rayon du feu
        light_radius = max(4, int(Sizes.TRAFFIC_LIGHT_RADIUS * zoom))

        # 2. Définir les décalages en PIXELS
        # On se place au bord du noeud + une petite marge
        offset_back_px = node_radius_visual + 5

        # On se place au bord de la route + rayon du feu + petite marge
        offset_side_px = (road_width_visual / 2) + light_radius + 2

        for node_id, intersection in graph.intersections.items():
            if not hasattr(intersection, "get_state"):
                continue

            # Position centrale du carrefour EN ECRAN
            node_data = graph.get_node(node_id)
            # On convertit tout de suite en pixels
            cx, cy = camera_convert_func((node_data['x'], node_data['y']))

            incoming_nodes = graph.get_incoming_nodes(node_id)
            for inc_node in incoming_nodes:
                state = intersection.get_state(inc_node)
                color = Colors.TL_GREEN if state == "GREEN" else Colors.TL_RED

                # Position source EN ECRAN
                inc_data = graph.get_node(inc_node)
                ix, iy = camera_convert_func((inc_data['x'], inc_data['y']))

                # Vecteur : Du Centre vers la Source (Vers l'arrière de la route)
                vx, vy = ix - cx, iy - cy
                dist = math.hypot(vx, vy)

                if dist < 1: continue

                # Normalisation (Direction arrière)
                ux, uy = vx / dist, vy / dist

                # Perpendiculaire pour aller sur le côté DROIT de la route (dans le sens entrant)
                # Si on regarde du centre vers la source, la droite de la route est à notre gauche.
                # Vecteur normal (-y, x) applique une rotation de 90°
                px, py = -uy, ux

                # Calcul final en pixels directement
                # Centre + (Recul vers l'arrière) + (Décalage côté)
                lx = cx + (ux * offset_back_px) + (px * offset_side_px)
                ly = cy + (uy * offset_back_px) + (py * offset_side_px)

                pygame.draw.circle(self.screen, Colors.TL_OUTLINE, (int(lx), int(ly)), light_radius + 1)
                pygame.draw.circle(self.screen, color, (int(lx), int(ly)), light_radius)

    def draw_edge(self, src_pos: Tuple[float, float], dst_pos: Tuple[float, float],
                  edge, src: str, dst: str, is_hovered: bool, zoom: float):

        base_width = Sizes.ROAD_WIDTH_BASE * zoom
        current_width = int(max(2, min(20, int(base_width))))

        if is_hovered:
            current_width += 2

        # Gestion des doubles routes (offset)
        start_draw, end_draw = src_pos, dst_pos
        if self.is_bidirectional(src, dst):
            offset_dist = max(4, min(15, int((Sizes.ROAD_SEPARATION / 2) * zoom)))
            start_draw, end_draw = offset_line(src_pos, dst_pos, -offset_dist)

        # Dessin de la route avec couleur basée sur la congestion
        color = self._get_traffic_color(edge)
        if is_hovered:
            color = Colors.ROAD_HOVER

        pygame.draw.line(self.screen, color, start_draw, end_draw, current_width)

        # Flèches de direction
        dx = end_draw[0] - start_draw[0]
        dy = end_draw[1] - start_draw[1]
        length = math.hypot(dx, dy)

        if length > 40:
            arrow_size = max(5, min(12, int(Sizes.ARROW_SIZE * zoom)))
            arrow_points = get_arrow_points(start_draw, end_draw, arrow_size)
            arrow_color = Colors.TEXT_DIM
            pygame.draw.polygon(self.screen, arrow_color, arrow_points)

        # Différencier le rendu selon le type d'edge
        if hasattr(edge, 'cells'):
            # Modèle cellular : points discrets
            self._draw_cellular_vehicles(start_draw, end_draw, edge, zoom)
        elif hasattr(edge, 'get_vehicle_positions'):
            # Modèle fluide : visualisation continue
            self._draw_fluid_traffic(start_draw, end_draw, edge, zoom, current_width)

    def _draw_cellular_vehicles(self, start_pos: Tuple[float, float],
                                end_pos: Tuple[float, float], edge, zoom: float):
        """Dessine les véhicules discrets pour le modèle cellular avec effet de trainée"""
        vehicle_radius = int(max(3, min(8, int(Sizes.VEHICLE_RADIUS * zoom))))

        # Pour les calculs de position
        dx_total = end_pos[0] - start_pos[0]
        dy_total = end_pos[1] - start_pos[1]

        for i, vehicle in enumerate(edge.cells):
            if vehicle is not None:
                # Position actuelle (centre de la cellule)
                t_current = (i + 0.5) / edge.distance
                x = start_pos[0] + t_current * dx_total
                y = start_pos[1] + t_current * dy_total

                # --- AJOUT : Effet de trainée (Trail) ---
                # Dans le modèle cellulaire, la vitesse = nombre de cases parcourues.
                # On dessine une trainée vers l'arrière proportionnelle à la vitesse.
                if vehicle.speed > 0:
                    # On estime la position précédente (d'où vient la voiture)
                    # On limite à 0 pour ne pas sortir de la route
                    prev_i = max(0, i - vehicle.speed)
                    t_prev = (prev_i + 0.5) / edge.distance

                    x_prev = start_pos[0] + t_prev * dx_total
                    y_prev = start_pos[1] + t_prev * dy_total

                    # Couleur de trainée semi-transparente
                    # Note: Pygame gère mal l'alpha sur draw.line direct,
                    # mais avec une couleur un peu plus sombre ça fait l'illusion.
                    trail_color = (100, 150, 220)
                    trail_width = max(2, vehicle_radius)  # Un peu plus fin que la voiture

                    pygame.draw.line(self.screen, trail_color,
                                     (int(x_prev), int(y_prev)),
                                     (int(x), int(y)),
                                     trail_width)

                # Dessin du véhicule (par dessus la trainée)
                # On change la couleur si le véhicule est à l'arrêt (speed=0) -> Rouge foncé
                color = Colors.VEHICLE
                if vehicle.speed == 0:
                    color = (200, 50, 50)  # Rouge si bloqué

                pygame.draw.circle(self.screen, color, (int(x), int(y)), vehicle_radius)

    def _draw_fluid_traffic(self, start_pos: Tuple[float, float],
                            end_pos: Tuple[float, float], edge, zoom: float, road_width: int):
        """
        Dessine le trafic fluide avec des segments colorés représentant la densité locale.
        Plus réaliste pour le modèle LWR.
        """
        if len(edge.vehicles) == 0:
            return

        # Option 1: Dessiner des véhicules semi-transparents avec trainée
        vehicle_radius = int(max(2, min(6, int(Sizes.VEHICLE_RADIUS * zoom * 0.8))))

        # Calculer la vitesse moyenne pour l'effet de trainée
        avg_speed = sum(v.speed for v in edge.vehicles) / len(edge.vehicles) if edge.vehicles else 0
        trail_length = max(0, min(0.15, avg_speed / edge.vmax * 0.15))  # Trainée proportionnelle à la vitesse

        for vehicle, ratio in edge.get_vehicle_positions():
            # Position actuelle
            x = start_pos[0] + ratio * (end_pos[0] - start_pos[0])
            y = start_pos[1] + ratio * (end_pos[1] - start_pos[1])

            # Dessiner une trainée si le véhicule va vite
            if trail_length > 0.01 and ratio > trail_length:
                # Position de début de trainée
                trail_ratio = ratio - trail_length
                x_trail = start_pos[0] + trail_ratio * (end_pos[0] - start_pos[0])
                y_trail = start_pos[1] + trail_ratio * (end_pos[1] - start_pos[1])

                # Trainée dégradée
                trail_color = (*Colors.VEHICLE[:2], Colors.VEHICLE[2], 80)  # Semi-transparent
                pygame.draw.line(self.screen, trail_color,
                                 (int(x_trail), int(y_trail)),
                                 (int(x), int(y)),
                                 max(2, vehicle_radius))

            # Véhicule principal
            pygame.draw.circle(self.screen, Colors.VEHICLE, (int(x), int(y)), vehicle_radius)

            # Option: ajouter un indicateur de vitesse (petit trait)
            if zoom > 1.5:  # Seulement si assez zoomé
                speed_ratio = vehicle.speed / edge.vmax if edge.vmax > 0 else 0
                indicator_length = 5 * zoom * speed_ratio

                if indicator_length > 2:
                    angle = math.atan2(end_pos[1] - start_pos[1], end_pos[0] - start_pos[0])
                    end_x = x + indicator_length * math.cos(angle)
                    end_y = y + indicator_length * math.sin(angle)
                    pygame.draw.line(self.screen, (255, 255, 255),
                                     (int(x), int(y)), (int(end_x), int(end_y)), 2)

    def _get_traffic_color(self, edge) -> Tuple[int, int, int]:
        """Calcule la couleur basée sur l'occupation normalisée"""
        try:
            occupation = edge.get_occupation_ratio()
        except:
            # Fallback si get_occupation_ratio n'est pas implémenté
            if hasattr(edge, 'cells'):
                occupation = sum(1 for c in edge.cells if c) / max(edge.distance, 1)
            elif hasattr(edge, 'vehicles') and hasattr(edge, 'max_vehicles'):
                occupation = len(edge.vehicles) / max(edge.max_vehicles, 1)
            else:
                occupation = 0.0

        # Gradation plus nuancée pour le modèle fluide
        if occupation < 0.2:
            # Très fluide : vert
            t = occupation / 0.2
            return lerp_color(Colors.TRAFFIC_LOW, Colors.TRAFFIC_LOW, t)
        elif occupation < 0.5:
            # Fluide modéré : vert -> jaune
            t = (occupation - 0.2) / 0.3
            return lerp_color(Colors.TRAFFIC_LOW, Colors.TRAFFIC_MEDIUM, t)
        elif occupation < 0.8:
            # Congestionné : jaune -> orange
            t = (occupation - 0.5) / 0.3
            orange = (255, 140, 60)
            return lerp_color(Colors.TRAFFIC_MEDIUM, orange, t)
        else:
            # Très congestionné : orange -> rouge
            t = (occupation - 0.8) / 0.2
            orange = (255, 140, 60)
            return lerp_color(orange, Colors.TRAFFIC_HIGH, t)

    def draw_node(self, pos: Tuple[float, float], node_id: str,
                  is_hovered: bool, is_entrance: bool, zoom: float):

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
        if radius > 15:
            if radius > 25:
                font = self.font_medium
            else:
                font = self.font_tiny

            text_surf = font.render(str(node_id), True, Colors.TEXT)
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
            "R: Reset View"
        ]

        y = 50
        for line in help_text:
            surf = self.font_tiny.render(line, True, Colors.TEXT_DIM)
            self.screen.blit(surf, (20, y))
            y += 15

    def draw_legend(self, screen_width: int, screen_height: int):
        """Dessine une légende des couleurs de trafic"""
        legend_x = screen_width - 150
        legend_y = 20
        legend_width = 130
        legend_height = 110

        # Background
        s = pygame.Surface((legend_width, legend_height), pygame.SRCALPHA)
        s.fill(Colors.INFO_BG)
        pygame.draw.rect(s, Colors.INFO_BORDER, s.get_rect(), 1)
        self.screen.blit(s, (legend_x, legend_y))

        # Title
        title_surf = self.font_small.render("Traffic", True, Colors.TEXT)
        self.screen.blit(title_surf, (legend_x + 10, legend_y + 10))

        # Color gradient
        gradient_width = 20
        gradient_height = 60
        gradient_x = legend_x + 10
        gradient_y = legend_y + 35

        # Dessiner le gradient
        for i in range(gradient_height):
            ratio = i / gradient_height
            if ratio < 0.25:
                color = Colors.TRAFFIC_LOW
            elif ratio < 0.625:
                t = (ratio - 0.25) / 0.375
                color = lerp_color(Colors.TRAFFIC_LOW, Colors.TRAFFIC_MEDIUM, t)
            else:
                t = (ratio - 0.625) / 0.375
                color = lerp_color(Colors.TRAFFIC_MEDIUM, Colors.TRAFFIC_HIGH, t)

            pygame.draw.line(self.screen, color,
                             (gradient_x, gradient_y + i),
                             (gradient_x + gradient_width, gradient_y + i))

        # Labels
        low_surf = self.font_tiny.render("Low", True, Colors.TEXT_DIM)
        high_surf = self.font_tiny.render("High", True, Colors.TEXT_DIM)

        self.screen.blit(low_surf, (gradient_x + gradient_width + 5, gradient_y))
        self.screen.blit(high_surf, (gradient_x + gradient_width + 5, gradient_y + gradient_height - 10))
