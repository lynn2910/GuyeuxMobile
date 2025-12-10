"""
Modern traffic simulation visualizer with camera controls and improved rendering.
"""

import pygame
from typing import Optional, Tuple
from ui.camera import Camera
from ui.renderer import Renderer
from ui.styles import Colors, Sizes, Animation
from ui.geometry import is_point_near_segment


class Visualizer:
    """
    Main visualizer class that orchestrates rendering and interaction.
    """

    def __init__(self, graph, width: int = 1400, height: int = 900):
        """
        Initialize the visualizer.

        :param graph: RoadGraph instance
        :param width: Window width
        :param height: Window height
        """
        pygame.init()

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Traffic Simulation - Modern View")

        self.graph = graph
        self.running = True
        self.current_tick = 0

        # Initialize subsystems
        self.camera = Camera(width, height)
        self.renderer = Renderer(self.screen)

        # UI state
        self.hovered_node = None
        self.hovered_edge = None

        # Initialize
        self._compute_world_positions()
        self._fit_camera_to_content()
        self.renderer.detect_bidirectional_edges(graph)

        # Clock for frame rate control
        self.clock = pygame.time.Clock()

    def _compute_world_positions(self):
        """
        Compute world positions for all nodes based on their graph coordinates.
        """
        nodes = list(self.graph.graph.nodes(data=True))

        if not nodes:
            return

        # Store positions in world coordinates (we'll transform them via camera)
        self.world_positions = {}
        for node_id, data in nodes:
            # Use graph coordinates as world coordinates
            self.world_positions[node_id] = (float(data['x']), float(data['y']))

    def _fit_camera_to_content(self):
        """Adjust camera to fit all graph content"""
        if not self.world_positions:
            return

        positions = list(self.world_positions.values())
        min_x = min(p[0] for p in positions)
        max_x = max(p[0] for p in positions)
        min_y = min(p[0] for p in positions)
        max_y = max(p[1] for p in positions)

        self.camera.fit_bounds(min_x, max_x, min_y, max_y, margin=Sizes.MARGIN)

    def _get_mouse_pos(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return pygame.mouse.get_pos()

    def _check_node_hover(self, mouse_pos: Tuple[int, int]) -> Optional[str]:
        """
        Check if mouse is hovering over a node.

        :param mouse_pos: Mouse position in screen coordinates
        :return: Node ID if hovering, None otherwise
        """
        for node_id, world_pos in self.world_positions.items():
            screen_pos = self.camera.world_to_screen(world_pos)

            # Calculate distance
            dx = mouse_pos[0] - screen_pos[0]
            dy = mouse_pos[1] - screen_pos[1]
            dist = (dx * dx + dy * dy) ** 0.5

            if dist <= Sizes.NODE_RADIUS_HOVER:
                return node_id

        return None

    def _check_edge_hover(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[str, str, dict]]:
        """
        Check if mouse is hovering over an edge.

        :param mouse_pos: Mouse position in screen coordinates
        :return: (src, dst, data) tuple if hovering, None otherwise
        """
        threshold = 15

        for src, dst, data in self.graph.get_edges():
            src_world = self.world_positions[src]
            dst_world = self.world_positions[dst]

            src_screen = self.camera.world_to_screen(src_world)
            dst_screen = self.camera.world_to_screen(dst_world)

            if is_point_near_segment(mouse_pos, src_screen, dst_screen, threshold):
                return (src, dst, data)

        return None

    def update(self, current_tick: int):
        """
        Update and render the visualization.

        :param current_tick: Current simulation tick
        """
        self.current_tick = current_tick
        mouse_pos = self._get_mouse_pos()

        # Update hover state
        self.hovered_node = self._check_node_hover(mouse_pos)
        if not self.hovered_node:
            self.hovered_edge = self._check_edge_hover(mouse_pos)
        else:
            self.hovered_edge = None

        # Render
        self._render()

        # Cap frame rate
        self.clock.tick(Animation.TARGET_FPS)

    def _render(self):
        """Perform all rendering"""
        self.renderer.clear()

        # Draw all edges first (so they appear behind nodes)
        for src, dst, data in self.graph.get_edges():
            edge = data['object']
            src_world = self.world_positions[src]
            dst_world = self.world_positions[dst]

            # Transform to screen coordinates
            src_screen = self.camera.world_to_screen(src_world)
            dst_screen = self.camera.world_to_screen(dst_world)

            # Check if this edge is hovered
            is_hovered = (self.hovered_edge and
                          self.hovered_edge[0] == src and
                          self.hovered_edge[1] == dst)

            self.renderer.draw_edge(src_screen, dst_screen, edge, src, dst, is_hovered)

        # Draw all nodes
        for node_id, world_pos in self.world_positions.items():
            screen_pos = self.camera.world_to_screen(world_pos)
            is_hovered = (node_id == self.hovered_node)

            # Check if this is an entrance (you can customize this logic)
            is_entrance = "entrance" in node_id.lower()

            self.renderer.draw_node(screen_pos, node_id, is_hovered, is_entrance)

        # Draw UI elements
        self.renderer.draw_tick_counter(self.current_tick)
        self.renderer.draw_controls_help()

        # Draw hover info
        if self.hovered_node:
            self._draw_node_info(self._get_mouse_pos(), self.hovered_node)
        elif self.hovered_edge:
            self._draw_edge_info(self._get_mouse_pos(), self.hovered_edge)

        pygame.display.flip()

    def _draw_node_info(self, mouse_pos: Tuple[int, int], node_id: str):
        """Draw information box for a node"""
        node_data = self.graph.get_node(node_id)
        lines = [
            f"Position: ({node_data['x']:.1f}, {node_data['y']:.1f})"
        ]
        self.renderer.draw_info_box(
            (mouse_pos[0] + 15, mouse_pos[1] + 15),
            lines,
            title=f"Node: {node_id}"
        )

    def _draw_edge_info(self, mouse_pos: Tuple[int, int], edge_data):
        """Draw information box for an edge"""
        src, dst, data = edge_data
        edge = data['object']

        lines = [f"Distance: {edge.distance}"]

        if hasattr(edge, 'get_infos'):
            lines.extend(edge.get_infos())

        self.renderer.draw_info_box(
            (mouse_pos[0] + 15, mouse_pos[1] + 15),
            lines,
            title=f"Edge: {src} → {dst}"
        )

    def handle_events(self) -> bool:
        """
        Handle pygame events.

        :return: False if should quit, True otherwise
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return False
                elif event.key == pygame.K_r:
                    # Reset camera
                    self._fit_camera_to_content()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:  # Middle mouse button
                    self.camera.start_pan(event.pos)
                elif event.button == 4:  # Scroll up (zoom in)
                    self.camera.zoom_at(event.pos, 1)
                elif event.button == 5:  # Scroll down (zoom out)
                    self.camera.zoom_at(event.pos, -1)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:  # Middle mouse button
                    self.camera.end_pan()

            elif event.type == pygame.MOUSEMOTION:
                if self.camera.is_panning:
                    self.camera.update_pan(event.pos)

        return True

    @staticmethod
    def close():
        """Clean up and close pygame"""
        pygame.quit()
