"""
Visual configuration and color schemes for the traffic simulation visualizer.
"""


class Colors:
    """Color palette for the visualizer (Light Theme)"""

    # Background
    BG = (250, 250, 250)
    BG_LIGHT = (255, 255, 255)

    # Roads
    ROAD_BASE = (200, 200, 200)
    ROAD_HOVER = (160, 160, 160)
    ROAD_OUTLINE = (180, 180, 180)

    # Traffic density colors (Interpolation Green -> Yellow -> Red)
    TRAFFIC_LOW = (100, 200, 100)
    TRAFFIC_MEDIUM = (255, 200, 50)
    TRAFFIC_HIGH = (255, 80, 80)

    # Nodes
    NODE_BASE = (255, 255, 255)
    NODE_HOVER = (240, 240, 255)
    NODE_OUTLINE = (50, 50, 50)
    NODE_ENTRANCE = (50, 50, 50)

    # Vehicles
    VEHICLE = (50, 100, 200)

    # UI Elements
    TEXT = (20, 20, 20)
    TEXT_DIM = (100, 100, 100)
    INFO_BG = (255, 255, 255, 230)
    INFO_BORDER = (200, 200, 200)


class Sizes:
    """Size constants for visual elements"""

    NODE_RADIUS_BASE = 12
    NODE_RADIUS_HOVER = 15
    NODE_OUTLINE_WIDTH = 2

    # Roads
    ROAD_WIDTH_BASE = 8
    ROAD_WIDTH_HOVER = 10
    ROAD_SEPARATION = 12

    # Vehicles
    VEHICLE_RADIUS = 4

    # UI
    ARROW_SIZE = 10
    INFO_PADDING = 10
    INFO_LINE_HEIGHT = 20
    MARGIN = 50


class Fonts:
    """Font configuration"""
    LARGE = 24
    MEDIUM = 18
    SMALL = 14
    TINY = 12


class Animation:
    """Animation and timing constants"""
    ZOOM_SPEED = 0.1
    TARGET_FPS = 144
