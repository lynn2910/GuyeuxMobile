"""
Visual configuration and color schemes for the traffic simulation visualizer.
"""


class Colors:
    """Color palette for the visualizer"""

    # Background
    BG = (15, 23, 42)  # Dark blue-gray
    BG_LIGHT = (30, 41, 59)

    # Roads
    ROAD_BASE = (71, 85, 105)
    ROAD_HOVER = (100, 116, 139)
    ROAD_OUTLINE = (51, 65, 85)

    # Traffic density colors (green -> yellow -> red)
    TRAFFIC_LOW = (34, 197, 94)  # Green
    TRAFFIC_MEDIUM = (234, 179, 8)  # Yellow
    TRAFFIC_HIGH = (239, 68, 68)  # Red

    # Nodes
    NODE_BASE = (59, 130, 246)  # Blue
    NODE_HOVER = (96, 165, 250)
    NODE_OUTLINE = (37, 99, 235)
    NODE_ENTRANCE = (168, 85, 247)  # Purple for entrances

    # Vehicles
    VEHICLE = (239, 68, 68)  # Red
    VEHICLE_TRAIL = (248, 113, 113)  # Light red

    # UI Elements
    TEXT = (241, 245, 249)  # Light gray
    TEXT_DIM = (148, 163, 184)
    INFO_BG = (30, 41, 59, 230)  # Semi-transparent
    INFO_BORDER = (51, 65, 85)

    # Grid
    GRID_MAJOR = (51, 65, 85, 128)
    GRID_MINOR = (51, 65, 85, 64)


class Sizes:
    """Size constants for visual elements"""

    # Nodes
    NODE_RADIUS = 12
    NODE_RADIUS_HOVER = 16
    NODE_OUTLINE_WIDTH = 2

    # Roads
    ROAD_WIDTH_BASE = 8
    ROAD_WIDTH_HOVER = 12
    ROAD_OUTLINE_WIDTH = 2
    ROAD_SEPARATION = 6  # Distance between bidirectional roads

    # Vehicles
    VEHICLE_RADIUS = 5
    VEHICLE_TRAIL_LENGTH = 3

    # Arrows
    ARROW_SIZE = 12
    ARROW_SPACING = 80  # Distance between arrows on long roads

    # UI
    INFO_PADDING = 12
    INFO_LINE_HEIGHT = 24
    MARGIN = 60


class Fonts:
    """Font configuration"""

    LARGE = 28
    MEDIUM = 20
    SMALL = 16
    TINY = 14


class Animation:
    """Animation and timing constants"""

    HOVER_FADE_SPEED = 0.15
    ZOOM_SPEED = 0.1
    PAN_SMOOTH = 0.2

    # Target FPS
    TARGET_FPS = 60
