"""
Main visualizer class for the traffic simulation.
Handles rendering, user input, and camera controls.
OPTIMIZED VERSION with spatial indexing and better rendering order.
"""
import ctypes
import pygame
from typing import Optional, Tuple, Set, Dict
from ui.camera import Camera
from ui.renderer import Renderer
from ui.styles import Sizes, Animation
from ui.geometry import is_point_near_segment

# Attempt to set high DPI awareness for sharper rendering on Windows.
try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass


class SpatialGrid:
    """
    Structure de données spatiale simple pour accélérer les requêtes de proximité.
    Divise l'espace en cellules pour éviter de tester tous les éléments.
    """

    def __init__(self, cell_size=100):
        self.cell_size = cell_size
        self.grid = {}

    def _get_cell(self, x, y):
        return (int(x // self.cell_size), int(y // self.cell_size))

    def _get_cells_for_bounds(self, min_x, max_x, min_y, max_y):
        """Retourne toutes les cellules touchées par une boîte englobante"""
        cells = set()
        min_cell_x = int(min_x // self.cell_size)
        max_cell_x = int(max_x // self.cell_size)
        min_cell_y = int(min_y // self.cell_size)
        max_cell_y = int(max_y // self.cell_size)

        for cx in range(min_cell_x, max_cell_x + 1):
            for cy in range(min_cell_y, max_cell_y + 1):
                cells.add((cx, cy))
        return cells

    def add_node(self, node_id, x, y):
        cell = self._get_cell(x, y)
        if cell not in self.grid:
            self.grid[cell] = {'nodes': [], 'edges': []}
        self.grid[cell]['nodes'].append((node_id, x, y))

    def add_edge(self, src, dst, src_pos, dst_pos, data):
        # Ajouter l'edge à toutes les cellules qu'il traverse
        min_x = min(src_pos[0], dst_pos[0])
        max_x = max(src_pos[0], dst_pos[0])
        min_y = min(src_pos[1], dst_pos[1])
        max_y = max(src_pos[1], dst_pos[1])

        cells = self._get_cells_for_bounds(min_x, max_x, min_y, max_y)
        for cell in cells:
            if cell not in self.grid:
                self.grid[cell] = {'nodes': [], 'edges': []}
            self.grid[cell]['edges'].append((src, dst, src_pos, dst_pos, data))

    def query_nodes(self, x, y, radius):
        """Trouve tous les nœuds dans un rayon donné"""
        cells = self._get_cells_for_bounds(x - radius, x + radius, y - radius, y + radius)
        results = []
        for cell in cells:
            if cell in self.grid:
                for node_id, nx, ny in self.grid[cell]['nodes']:
                    dist_sq = (x - nx) ** 2 + (y - ny) ** 2
                    if dist_sq <= radius ** 2:
                        results.append((node_id, nx, ny, dist_sq))
        return results

    def query_edges(self, min_x, max_x, min_y, max_y):
        """Trouve tous les edges dans une région"""
        cells = self._get_cells_for_bounds(min_x, max_x, min_y, max_y)
        results = []
        seen = set()
        for cell in cells:
            if cell in self.grid:
                for edge_data in self.grid[cell]['edges']:
                    edge_key = (edge_data[0], edge_data[1])
                    if edge_key not in seen:
                        seen.add(edge_key)
                        results.append(edge_data)
        return results


class Visualizer:
    """
    Main class that orchestrates the visualization of the simulation.
    OPTIMIZED VERSION with spatial indexing and better rendering.
    """

    def __init__(self, graph, width: int = 1400, height: int = 900):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Traffic Simulation")

        self.graph = graph
        self.running = True
        self.current_tick = 0

        # Initialize core components.
        self.camera = Camera(width, height)
        self.renderer = Renderer(self.screen)

        # UI state variables.
        self.hovered_node = None
        self.hovered_edge = None
        self.show_legend = True

        # Pre-computation steps.
        self._compute_world_positions()
        self._build_spatial_index()
        self._fit_camera_to_content()
        self.renderer.detect_bidirectional_edges(graph)

        self.clock = pygame.time.Clock()

        # Cache pour le hover
        self._last_hover_check_pos = None
        self._hover_check_cooldown = 0

    def _compute_world_positions(self):
        """Caches the world coordinates of each node from the graph data."""
        self.world_positions = {
            node_id: (float(data['x']), float(data['y']))
            for node_id, data in self.graph.graph.nodes(data=True)
        }

    def _build_spatial_index(self):
        """Construit un index spatial pour accélérer les requêtes de proximité."""
        self.spatial_grid = SpatialGrid(cell_size=200)

        # Indexer les nœuds
        for node_id, (x, y) in self.world_positions.items():
            self.spatial_grid.add_node(node_id, x, y)

        # Indexer les edges
        for src, dst, data in self.graph.get_edges():
            src_pos = self.world_positions[src]
            dst_pos = self.world_positions[dst]
            self.spatial_grid.add_edge(src, dst, src_pos, dst_pos, data)

    def _fit_camera_to_content(self):
        """Adjusts the camera's zoom and position to fit the entire graph."""
        if not self.world_positions:
            return
        positions = list(self.world_positions.values())
        min_x = min(p[0] for p in positions)
        max_x = max(p[0] for p in positions)
        min_y = min(p[1] for p in positions)
        max_y = max(p[1] for p in positions)
        self.camera.fit_bounds(min_x, max_x, min_y, max_y, margin=Sizes.MARGIN)

    @staticmethod
    def _get_mouse_pos() -> Tuple[int, int]:
        """Returns the current mouse position on the screen."""
        return pygame.mouse.get_pos()

    def _check_node_hover(self, mouse_pos: Tuple[int, int]) -> Optional[str]:
        """
        Checks if the mouse is hovering over any node.
        OPTIMIZED: Utilise l'index spatial.
        """
        # Convertir la position de la souris en coordonnées mondiales
        world_pos = self.camera.screen_to_world(mouse_pos)
        detection_radius = max(10, min(35, Sizes.NODE_RADIUS_HOVER * self.camera.zoom)) + 5

        # Recherche spatiale
        candidates = self.spatial_grid.query_nodes(world_pos[0], world_pos[1], detection_radius)

        if not candidates:
            return None

        # Trouver le nœud le plus proche
        closest = min(candidates, key=lambda x: x[3])  # x[3] = dist_sq
        return closest[0]

    def _check_edge_hover(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[str, str, dict]]:
        """
        Checks if the mouse is hovering over any edge.
        OPTIMIZED: Utilise l'index spatial et évite les calculs inutiles.
        """
        world_pos = self.camera.screen_to_world(mouse_pos)
        threshold = max(6, min(20, 10 * self.camera.zoom))

        # Définir une région de recherche autour de la souris
        search_radius = threshold + 50  # Marge de sécurité
        min_x, max_x = world_pos[0] - search_radius, world_pos[0] + search_radius
        min_y, max_y = world_pos[1] - search_radius, world_pos[1] + search_radius

        # Recherche spatiale
        candidate_edges = self.spatial_grid.query_edges(min_x, max_x, min_y, max_y)

        for src, dst, src_pos, dst_pos, data in candidate_edges:
            src_screen = self.camera.world_to_screen(src_pos)
            dst_screen = self.camera.world_to_screen(dst_pos)

            # Adjust check for bidirectional edges that are drawn offset.
            if self.renderer.is_bidirectional(src, dst):
                from ui.geometry import offset_line
                base_separation = Sizes.ROAD_SEPARATION if self.camera.zoom >= 0.5 else Sizes.ROAD_SEPARATION * 0.6
                offset_dist = max(3, min(15, (base_separation / 2) * self.camera.zoom))
                src_screen, dst_screen = offset_line(src_screen, dst_screen, -offset_dist)

            if is_point_near_segment(mouse_pos, src_screen, dst_screen, threshold):
                return (src, dst, data)

        return None

    def update(self, current_tick: int):
        """
        Called by the main simulation loop to update the visualizer's state and redraw the screen.
        OPTIMIZED: Limite les vérifications de hover.
        """
        self.current_tick = current_tick
        mouse_pos = self._get_mouse_pos()

        # Vérifier le hover seulement tous les N frames ou si la souris a bougé
        self._hover_check_cooldown -= 1
        if self._hover_check_cooldown <= 0 or self._last_hover_check_pos != mouse_pos:
            self.hovered_node = self._check_node_hover(mouse_pos)
            self.hovered_edge = None if self.hovered_node else self._check_edge_hover(mouse_pos)
            self._last_hover_check_pos = mouse_pos
            self._hover_check_cooldown = 3  # Vérifier tous les 3 frames

        self._render()
        self.clock.tick(Animation.TARGET_FPS)

    def _render(self):
        """
        Renders the entire scene.
        OPTIMIZED: Ordre de rendu amélioré (edges d'abord, puis nodes par-dessus).
        """
        self.renderer.clear()
        zoom = self.camera.zoom

        min_x, max_x, min_y, max_y = self._get_visible_bounds()

        # 1. Déterminer les nœuds visibles
        visible_nodes = set()
        for node_id, pos in self.world_positions.items():
            if min_x <= pos[0] <= max_x and min_y <= pos[1] <= max_y:
                visible_nodes.add(node_id)

        # 2. DESSINER LES EDGES EN PREMIER (pour qu'ils soient sous les nœuds)
        for src, dst, data in self.graph.get_edges():
            # Culling amélioré : vérifier si au moins un nœud est visible
            if src not in visible_nodes and dst not in visible_nodes:
                continue

            src_screen = self.camera.world_to_screen(self.world_positions[src])
            dst_screen = self.camera.world_to_screen(self.world_positions[dst])

            is_hovered = self.hovered_edge and \
                         self.hovered_edge[0] == src and self.hovered_edge[1] == dst

            self.renderer.draw_edge(src_screen, dst_screen, data['object'], src, dst, is_hovered, zoom)

        # 3. DESSINER LES NODES PAR-DESSUS (ils apparaissent maintenant au-dessus des edges)
        for node_id in visible_nodes:
            screen_pos = self.camera.world_to_screen(self.world_positions[node_id])
            is_hovered = node_id == self.hovered_node
            self.renderer.draw_node(screen_pos, node_id, is_hovered, zoom)

        # 4. Dessiner les traffic lights
        self.renderer.draw_traffic_lights(self.graph, self.camera.world_to_screen, zoom, visible_nodes)

        # 5. UI overlay
        self.renderer.draw_tick_counter(self.current_tick)
        self.renderer.draw_controls_help()
        if self.show_legend:
            self.renderer.draw_legend(self.width, self.height)

        # 6. Info boxes
        if self.hovered_node:
            self._draw_node_info(self._get_mouse_pos(), self.hovered_node)
        elif self.hovered_edge:
            self._draw_edge_info(self._get_mouse_pos(), self.hovered_edge)

        pygame.display.flip()

    def _draw_node_info(self, mouse_pos: Tuple[int, int], node_id: str):
        """Gathers and displays information for a hovered node."""
        node_data = self.graph.get_node(node_id)
        lines = [f"Pos: ({node_data['x']:.0f}, {node_data['y']:.0f})"]

        # Ajouter le nombre de connexions
        incoming = len(list(self.graph.graph.predecessors(node_id)))
        outgoing = len(list(self.graph.graph.successors(node_id)))
        lines.append(f"In: {incoming}, Out: {outgoing}")

        self.renderer.draw_info_box((mouse_pos[0] + 15, mouse_pos[1] + 15), lines, title=f"Node {node_id}")

    def _draw_edge_info(self, mouse_pos: Tuple[int, int], edge_data):
        """Gathers and displays information for a hovered edge."""
        src, dst, data = edge_data
        edge = data['object']
        title = f"Edge: {src} → {dst}"
        lines = edge.get_infos() if hasattr(edge, 'get_infos') else []
        self.renderer.draw_info_box((mouse_pos[0] + 15, mouse_pos[1] + 15), lines, title=title)

    def handle_events(self) -> bool:
        """
        Processes all user input from the Pygame event queue.
        Returns False if the simulation should exit.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                self.camera.width, self.camera.height = self.width, self.height
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_r:
                    self._fit_camera_to_content()
                if event.key == pygame.K_l:
                    self.show_legend = not self.show_legend
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 2):
                    self.camera.start_pan(event.pos)
                elif event.button == 4:
                    self.camera.zoom_at(event.pos, 1)  # Scroll up
                elif event.button == 5:
                    self.camera.zoom_at(event.pos, -1)  # Scroll down
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 2):
                    self.camera.end_pan()
            elif event.type == pygame.MOUSEMOTION:
                if self.camera.is_panning:
                    self.camera.update_pan(event.pos)
        return True

    def _get_visible_bounds(self):
        """
        Calcule les limites du viewport avec une marge.
        OPTIMIZED: Marge adaptative basée sur le zoom.
        """
        margin = max(50, 200 / self.camera.zoom)  # Marge plus grande à petit zoom
        min_x, min_y = self.camera.screen_to_world((-margin, -margin))
        max_x, max_y = self.camera.screen_to_world((self.width + margin, self.height + margin))
        return min_x, max_x, min_y, max_y

    @staticmethod
    def close():
        """Shuts down Pygame."""
        pygame.quit()
