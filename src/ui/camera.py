"""
Camera system for panning and zooming in the visualization.
"""

from typing import Tuple
from ui.styles import Animation


class Camera:
    """
    Handles viewport transformations (pan and zoom).
    """

    def __init__(self, width: int, height: int):
        """
        Initialize camera.

        :param width: Viewport width
        :param height: Viewport height
        """
        self.width = width
        self.height = height

        # Camera position (center of view in world coordinates)
        self.x = 0.0
        self.y = 0.0

        # Zoom level (1.0 = no zoom)
        self.zoom = 1.0
        self.target_zoom = 1.0

        # Panning state
        self.is_panning = False
        self.pan_start_mouse = (0, 0)
        self.pan_start_camera = (0.0, 0.0)

        # Constraints
        self.min_zoom = 0.1
        self.max_zoom = 5.0

    def start_pan(self, mouse_pos: Tuple[int, int]):
        """Start panning operation"""
        self.is_panning = True
        self.pan_start_mouse = mouse_pos
        self.pan_start_camera = (self.x, self.y)

    def update_pan(self, mouse_pos: Tuple[int, int]):
        """Update camera position during pan"""
        if not self.is_panning:
            return

        dx = (mouse_pos[0] - self.pan_start_mouse[0]) / self.zoom
        dy = (mouse_pos[1] - self.pan_start_mouse[1]) / self.zoom

        self.x = self.pan_start_camera[0] - dx
        self.y = self.pan_start_camera[1] - dy

    def end_pan(self):
        """End panning operation"""
        self.is_panning = False

    def zoom_at(self, mouse_pos: Tuple[int, int], delta: float):
        """
        Zoom towards/away from a specific point.

        :param mouse_pos: Mouse position in screen coordinates
        :param delta: Zoom delta (positive = zoom in, negative = zoom out)
        """
        # Calculate world position before zoom
        world_pos_before = self.screen_to_world(mouse_pos)

        # Update zoom
        zoom_factor = 1.0 + delta * Animation.ZOOM_SPEED
        self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * zoom_factor))

        # Smoothly interpolate zoom
        self.zoom += (self.target_zoom - self.zoom) * 0.3

        # Calculate world position after zoom
        world_pos_after = self.screen_to_world(mouse_pos)

        # Adjust camera to keep the same point under the mouse
        self.x += world_pos_before[0] - world_pos_after[0]
        self.y += world_pos_before[1] - world_pos_after[1]

    def world_to_screen(self, world_pos: Tuple[float, float]) -> Tuple[int, int]:
        """
        Convert world coordinates to screen coordinates.

        :param world_pos: Position in world space
        :return: Position in screen space
        """
        wx, wy = world_pos

        # Apply camera transform
        screen_x = (wx - self.x) * self.zoom + self.width / 2
        screen_y = (wy - self.y) * self.zoom + self.height / 2

        return (int(screen_x), int(screen_y))

    def screen_to_world(self, screen_pos: Tuple[int, int]) -> Tuple[float, float]:
        """
        Convert screen coordinates to world coordinates.

        :param screen_pos: Position in screen space
        :return: Position in world space
        """
        sx, sy = screen_pos

        # Inverse camera transform
        world_x = (sx - self.width / 2) / self.zoom + self.x
        world_y = (sy - self.height / 2) / self.zoom + self.y

        return (world_x, world_y)

    def reset(self):
        """Reset camera to default position and zoom"""
        self.x = 0.0
        self.y = 0.0
        self.zoom = 1.0
        self.target_zoom = 1.0

    def fit_bounds(self, min_x: float, max_x: float, min_y: float, max_y: float, margin: float = 60):
        """
        Adjust camera to fit all content in view.

        :param min_x: Minimum X coordinate
        :param max_x: Maximum X coordinate
        :param min_y: Minimum Y coordinate
        :param max_y: Maximum Y coordinate
        :param margin: Margin around content
        """
        # Calculate center
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Calculate required zoom to fit content
        range_x = max_x - min_x
        range_y = max_y - min_y

        if range_x == 0 or range_y == 0:
            self.zoom = 1.0
        else:
            zoom_x = (self.width - 2 * margin) / range_x
            zoom_y = (self.height - 2 * margin) / range_y
            self.zoom = min(zoom_x, zoom_y)

        # Clamp zoom
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom))
        self.target_zoom = self.zoom

        # Center camera
        self.x = center_x
        self.y = center_y
