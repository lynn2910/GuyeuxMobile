"""
Modern traffic simulation visualizer with camera controls and improved rendering.
"""
import ctypes

import pygame
from typing import Optional, Tuple
from ui.camera import Camera
from ui.renderer import Renderer
from ui.styles import Colors, Sizes, Animation
from ui.geometry import is_point_near_segment

try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass


class Visualizer:
    """
    Main visualizer class that orchestrates rendering and interaction.
    """

    def __init__(self, graph, width: int = 1400, height: int = 900):
        pygame.init()

        self.width = width
        self.height = height

        # Create resizable window
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Traffic Simulation - Light Theme")

        self.graph = graph
        self.running = True
        self.current_tick = 0

        # Initialize subsystems
        self.camera = Camera(width, height)
        self.renderer = Renderer(self.screen)

        # UI state
        self.hovered_node = None
        self.hovered_edge = None

        # Pre-calculations
        self._compute_world_positions()
        self._fit_camera_to_content()

        # Detect bidirectional edges to draw double roads
        self.renderer.detect_bidirectional_edges(graph)

        self.clock = pygame.time.Clock()

    def _compute_world_positions(self):
        """Compute world positions for all nodes based on their graph coordinates."""
        nodes = list(self.graph.graph.nodes(data=True))
        if not nodes:
            return
        self.world_positions = {}
        for node_id, data in nodes:
            self.world_positions[node_id] = (float(data['x']), float(data['y']))

    def _fit_camera_to_content(self):
        """Adjust camera to fit all graph content"""
        if not self.world_positions:
            return

        positions = list(self.world_positions.values())
        if not positions:
            return

        min_x = min(p[0] for p in positions)
        max_x = max(p[0] for p in positions)
        min_y = min(p[1] for p in positions)
        max_y = max(p[1] for p in positions)

        self.camera.fit_bounds(min_x, max_x, min_y, max_y, margin=Sizes.MARGIN)

    def _get_mouse_pos(self) -> Tuple[int, int]:
        return pygame.mouse.get_pos()

    def _check_node_hover(self, mouse_pos: Tuple[int, int]) -> Optional[str]:
        # --- CORRECTION HITBOX ---
        # On applique exactement la même logique que le Renderer :
        # La taille de détection ne doit pas dépasser la taille visuelle max (35px)

        zoom = self.camera.zoom
        # Rayon théorique
        base_radius = Sizes.NODE_RADIUS_HOVER * zoom

        # Rayon réel affiché (Clamped entre 10 et 35 pixels + marge de confort)
        detection_radius = max(10, min(35, base_radius)) + 5  # +5px de tolérance

        for node_id, world_pos in self.world_positions.items():
            screen_pos = self.camera.world_to_screen(world_pos)

            # Calcul de distance en pixels écran
            dx = mouse_pos[0] - screen_pos[0]
            dy = mouse_pos[1] - screen_pos[1]
            dist = (dx * dx + dy * dy) ** 0.5

            if dist <= detection_radius:
                return node_id

        return None

    def _check_edge_hover(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[str, str, dict]]:
        zoom = self.camera.zoom
        # Seuil de détection ajusté (env. la demi-largeur de la route)
        threshold = max(6, min(20, 10 * zoom))

        # On récupère l'offset utilisé par le renderer pour être cohérent
        base_offset = (Sizes.ROAD_SEPARATION / 2) * zoom

        for src, dst, data in self.graph.get_edges():
            src_world = self.world_positions[src]
            dst_world = self.world_positions[dst]

            # 1. Coordonnées écran de base (centre des nœuds)
            src_screen = self.camera.world_to_screen(src_world)
            dst_screen = self.camera.world_to_screen(dst_world)

            # 2. Calcul du décalage (Exactement comme dans Renderer.draw_edge)
            start_check, end_check = src_screen, dst_screen

            # On vérifie si c'est une route bidirectionnelle via le renderer
            # (car c'est lui qui détient la logique de détection des paires)
            if self.renderer.is_bidirectional(src, dst):
                # On applique le même décalage négatif que le renderer
                from ui.geometry import offset_line
                start_check, end_check = offset_line(src_screen, dst_screen, -base_offset)

            # 3. Vérification avec la ligne décalée
            if is_point_near_segment(mouse_pos, start_check, end_check, threshold):
                return (src, dst, data)

        return None

    def update(self, current_tick: int):
        self.current_tick = current_tick
        mouse_pos = self._get_mouse_pos()

        # Update hover state
        self.hovered_node = self._check_node_hover(mouse_pos)
        if not self.hovered_node:
            self.hovered_edge = self._check_edge_hover(mouse_pos)
        else:
            self.hovered_edge = None

        self._render()
        self.clock.tick(Animation.TARGET_FPS)

    def _render(self):
        self.renderer.clear()

        # Pass the zoom level to the renderer so it can scale elements
        zoom_level = self.camera.zoom

        # 1. Draw Edges
        for src, dst, data in self.graph.get_edges():
            edge = data['object']
            src_world = self.world_positions[src]
            dst_world = self.world_positions[dst]

            src_screen = self.camera.world_to_screen(src_world)
            dst_screen = self.camera.world_to_screen(dst_world)

            is_hovered = (self.hovered_edge and
                          self.hovered_edge[0] == src and
                          self.hovered_edge[1] == dst)

            self.renderer.draw_edge(src_screen, dst_screen, edge, src, dst, is_hovered, zoom_level)

        # 2. Draw Nodes
        for node_id, world_pos in self.world_positions.items():
            screen_pos = self.camera.world_to_screen(world_pos)
            is_hovered = (node_id == self.hovered_node)
            is_entrance = "entrance" in node_id.lower() or "source" in node_id.lower()

            self.renderer.draw_node(screen_pos, node_id, is_hovered, is_entrance, zoom_level)

        # 3. UI Overlays
        self.renderer.draw_tick_counter(self.current_tick)
        self.renderer.draw_controls_help()

        if self.hovered_node:
            self._draw_node_info(self._get_mouse_pos(), self.hovered_node)
        elif self.hovered_edge:
            self._draw_edge_info(self._get_mouse_pos(), self.hovered_edge)

        pygame.display.flip()

    def _draw_node_info(self, mouse_pos: Tuple[int, int], node_id: str):
        node_data = self.graph.get_node(node_id)
        lines = [f"Pos: ({node_data['x']:.0f}, {node_data['y']:.0f})"]
        self.renderer.draw_info_box((mouse_pos[0] + 15, mouse_pos[1] + 15), lines, title=f"Node {node_id}")

    def _draw_edge_info(self, mouse_pos: Tuple[int, int], edge_data):
        src, dst, data = edge_data
        edge = data['object']

        # Clean simple title
        title = f"{src} -> {dst}"

        lines = [f"Length: {edge.distance}m"]
        if hasattr(edge, 'get_infos'):
            lines.extend(edge.get_infos())

        self.renderer.draw_info_box((mouse_pos[0] + 15, mouse_pos[1] + 15), lines, title=title)

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False

            elif event.type == pygame.VIDEORESIZE:
                # Handle window resizing
                self.width = event.w
                self.height = event.h
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                self.camera.width = self.width
                self.camera.height = self.height
                # Optional: Refit content on resize
                # self._fit_camera_to_content()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return False
                elif event.key == pygame.K_r:
                    self._fit_camera_to_content()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Left click (1) or Middle click (2) for panning
                if event.button == 1 or event.button == 2:
                    self.camera.start_pan(event.pos)
                elif event.button == 4:  # Zoom In
                    self.camera.zoom_at(event.pos, 1)
                elif event.button == 5:  # Zoom Out
                    self.camera.zoom_at(event.pos, -1)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 or event.button == 2:
                    self.camera.end_pan()

            elif event.type == pygame.MOUSEMOTION:
                if self.camera.is_panning:
                    self.camera.update_pan(event.pos)

        return True

    @staticmethod
    def close():
        pygame.quit()
