"""
Geometric utilities for road rendering and positioning.
"""

import math
from typing import Tuple


def normalize_vector(vec: Tuple[float, float]) -> Tuple[float, float]:
    """Normalize a 2D vector"""
    x, y = vec
    length = math.sqrt(x * x + y * y)
    if length == 0:
        return (0, 0)
    return (x / length, y / length)


def perpendicular(vec: Tuple[float, float]) -> Tuple[float, float]:
    """Get perpendicular vector (rotated 90° counterclockwise)"""
    x, y = vec
    return (-y, x)


def offset_line(start: Tuple[float, float],
                end: Tuple[float, float],
                distance: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    Offset a line segment perpendicular to its direction.

    :param start: Start point (x, y)
    :param end: End point (x, y)
    :param distance: Offset distance (positive = left, negative = right)
    :return: New start and end points
    """
    # Direction vector
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    # Normalize and get perpendicular
    norm = normalize_vector((dx, dy))
    perp = perpendicular(norm)

    # Apply offset
    offset_x = perp[0] * distance
    offset_y = perp[1] * distance

    new_start = (start[0] + offset_x, start[1] + offset_y)
    new_end = (end[0] + offset_x, end[1] + offset_y)

    return new_start, new_end


def point_to_line_distance(point: Tuple[float, float],
                           line_start: Tuple[float, float],
                           line_end: Tuple[float, float]) -> float:
    """Calculate perpendicular distance from a point to a line segment"""
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end

    line_length_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if line_length_sq == 0:
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

    # Project point onto line
    t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_length_sq))
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)

    return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)


def is_point_near_segment(point: Tuple[float, float],
                          seg_start: Tuple[float, float],
                          seg_end: Tuple[float, float],
                          threshold: float = 10,
                          margin: float = 20) -> bool:
    """
    Check if a point is near a line segment.

    :param point: Point to test
    :param seg_start: Segment start
    :param seg_end: Segment end
    :param threshold: Maximum distance to consider "near"
    :param margin: Extra margin for bounding box check
    :return: True if point is near the segment
    """
    # First check bounding box (fast rejection)
    px, py = point
    x1, y1 = seg_start
    x2, y2 = seg_end

    min_x, max_x = min(x1, x2) - margin, max(x1, x2) + margin
    min_y, max_y = min(y1, y2) - margin, max(y1, y2) + margin

    if not (min_x <= px <= max_x and min_y <= py <= max_y):
        return False

    # Check actual distance
    dist = point_to_line_distance(point, seg_start, seg_end)
    return dist <= threshold


def interpolate_points(start: Tuple[float, float],
                       end: Tuple[float, float],
                       t: float) -> Tuple[float, float]:
    """
    Interpolate between two points.

    :param start: Start point
    :param end: End point
    :param t: Interpolation factor (0 to 1)
    :return: Interpolated point
    """
    x = start[0] + t * (end[0] - start[0])
    y = start[1] + t * (end[1] - start[1])
    return (x, y)


def get_arrow_points(start: Tuple[float, float],
                     end: Tuple[float, float],
                     size: float = 10) -> list:
    """
    Calculate arrow head points for a direction indicator.

    :param start: Line start point
    :param end: Line end point
    :param size: Arrow size
    :return: List of 3 points forming the arrow head
    """
    # Calculate angle
    angle = math.atan2(end[1] - start[1], end[0] - start[0])

    # Arrow head at midpoint
    mid_x = (start[0] + end[0]) / 2
    mid_y = (start[1] + end[1]) / 2

    # Three points of the arrow
    arrow_points = [
        (mid_x, mid_y),
        (mid_x - size * math.cos(angle - math.pi / 6),
         mid_y - size * math.sin(angle - math.pi / 6)),
        (mid_x - size * math.cos(angle + math.pi / 6),
         mid_y - size * math.sin(angle + math.pi / 6))
    ]

    return arrow_points


def lerp_color(color1: Tuple[int, int, int],
               color2: Tuple[int, int, int],
               t: float) -> Tuple[int, int, int]:
    """
    Linear interpolation between two RGB colors.

    :param color1: First color (r, g, b)
    :param color2: Second color (r, g, b)
    :param t: Interpolation factor (0 to 1)
    :return: Interpolated color
    """
    r = int(color1[0] + t * (color2[0] - color1[0]))
    g = int(color1[1] + t * (color2[1] - color1[1]))
    b = int(color1[2] + t * (color2[2] - color1[2]))
    return (r, g, b)
