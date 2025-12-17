"""
Main visualizer class for the traffic simulation.
Handles rendering, user input, and camera controls.
"""
import ctypes
import pygame
from typing import Optional, Tuple
from ui.camera import Camera
from ui.renderer import Renderer
from ui.styles import Sizes, Animation
from ui.geometry import is_point_near_segment

# Attempt to set high DPI awareness for sharper rendering on Windows.
try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass  # Fails on non-Windows systems, which is fine.


class Visualizer:
    """
    Main class that orchestrates the visualization of the simulation.

    It initializes Pygame, manages the main display window, and coordinates the
    Camera and Renderer to draw the simulation state. It also handles all user
    input for interaction, such as panning, zooming, and hovering.
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
        self._fit_camera_to_content()
        self.renderer.detect_bidirectional_edges(graph)

        self.clock = pygame.time.Clock()

    def _compute_world_positions(self):
        """Caches the world coordinates of each node from the graph data."""
        self.world_positions = {
            node_id: (float(data['x']), float(data['y']))
            for node_id, data in self.graph.graph.nodes(data=True)
        }

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
        """Checks if the mouse is hovering over any node."""
        detection_radius = max(10, min(35, Sizes.NODE_RADIUS_HOVER * self.camera.zoom)) + 5
        for node_id, world_pos in self.world_positions.items():
            screen_pos = self.camera.world_to_screen(world_pos)
            dist_sq = (mouse_pos[0] - screen_pos[0]) ** 2 + (mouse_pos[1] - screen_pos[1]) ** 2
            if dist_sq <= detection_radius ** 2:
                return node_id
        return None

    def _check_edge_hover(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[str, str, dict]]:
        """Checks if the mouse is hovering over any edge."""
        threshold = max(6, min(20, 10 * self.camera.zoom))
        for src, dst, data in self.graph.get_edges():
            src_screen = self.camera.world_to_screen(self.world_positions[src])
            dst_screen = self.camera.world_to_screen(self.world_positions[dst])

            # Adjust check for bidirectional edges that are drawn offset.
            if self.renderer.is_bidirectional(src, dst):
                from ui.geometry import offset_line
                offset_dist = max(4, min(15, (Sizes.ROAD_SEPARATION / 2) * self.camera.zoom))
                src_screen, dst_screen = offset_line(src_screen, dst_screen, -offset_dist)

            if is_point_near_segment(mouse_pos, src_screen, dst_screen, threshold):
                return (src, dst, data)
        return None

    def update(self, current_tick: int):
        """
        Called by the main simulation loop to update the visualizer's state and redraw the screen.
        """
        self.current_tick = current_tick
        mouse_pos = self._get_mouse_pos()

        # Update hover state based on mouse position.
        self.hovered_node = self._check_node_hover(mouse_pos)
        self.hovered_edge = None if self.hovered_node else self._check_edge_hover(mouse_pos)

        self._render()
        self.clock.tick(Animation.TARGET_FPS)

    def _render(self):
        """The main drawing sequence for a single frame."""
        self.renderer.clear()
        zoom = self.camera.zoom

        # 1. Draw all edges and the vehicles on them.
        for src, dst, data in self.graph.get_edges():
            src_screen = self.camera.world_to_screen(self.world_positions[src])
            dst_screen = self.camera.world_to_screen(self.world_positions[dst])
            is_hovered = self.hovered_edge and self.hovered_edge[0] == src and self.hovered_edge[1] == dst
            self.renderer.draw_edge(src_screen, dst_screen, data['object'], src, dst, is_hovered, zoom)

        # 2. Draw all nodes.
        for node_id, world_pos in self.world_positions.items():
            screen_pos = self.camera.world_to_screen(world_pos)
            is_hovered = node_id == self.hovered_node
            self.renderer.draw_node(screen_pos, node_id, is_hovered, zoom)

        # 3. Draw traffic lights.
        self.renderer.draw_traffic_lights(self.graph, self.camera.world_to_screen, zoom)

        # 4. Draw UI overlays (tick counter, help text, legend).
        self.renderer.draw_tick_counter(self.current_tick)
        self.renderer.draw_controls_help()
        if self.show_legend:
            self.renderer.draw_legend(self.width, self.height)

        # 5. Draw info boxes for hovered elements.
        if self.hovered_node:
            self._draw_node_info(self._get_mouse_pos(), self.hovered_node)
        elif self.hovered_edge:
            self._draw_edge_info(self._get_mouse_pos(), self.hovered_edge)

        pygame.display.flip()

    def _draw_node_info(self, mouse_pos: Tuple[int, int], node_id: str):
        """Gathers and displays information for a hovered node."""
        node_data = self.graph.get_node(node_id)
        lines = [f"Pos: ({node_data['x']:.0f}, {node_data['y']:.0f})"]
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
                if event.key == pygame.K_ESCAPE: return False
                if event.key == pygame.K_r: self._fit_camera_to_content()
                if event.key == pygame.K_l: self.show_legend = not self.show_legend
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 2):
                    self.camera.start_pan(event.pos)
                elif event.button == 4:
                    self.camera.zoom_at(event.pos, 1)  # Scroll up
                elif event.button == 5:
                    self.camera.zoom_at(event.pos, -1)  # Scroll down
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 2): self.camera.end_pan()
            elif event.type == pygame.MOUSEMOTION:
                if self.camera.is_panning: self.camera.update_pan(event.pos)
        return True

    @staticmethod
    def close():
        """Shuts down Pygame."""
        pygame.quit()
