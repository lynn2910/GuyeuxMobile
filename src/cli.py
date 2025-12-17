import argparse
import config


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments for the traffic simulation.

    This function sets up the argument parser, defines the expected command-line
    flags, and validates the provided inputs.

    Returns:
        An argparse.Namespace object containing the parsed arguments.
        - map (str): Path to the map file.
        - tps (float): Simulation ticks per second.
        - debug (bool): Flag to enable debug mode.
        - visualizer (bool): Flag to enable the graphical visualizer.
    """
    parser = argparse.ArgumentParser(
        description="Run a cellular automaton-based traffic simulation.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python main.py --map data/maps/simple_intersection.map --tps 10 --visualizer
  python main.py --map data/maps/grid.map --tps 5 --debug
        """
    )

    # Required argument for the map file.
    parser.add_argument(
        "--map",
        type=str,
        required=True,
        help="Path to the .map file defining the road network and simulation."
    )

    # Optional argument for simulation speed.
    parser.add_argument(
        "--tps",
        type=float,
        default=1.0,
        help="Ticks Per Second for the simulation loop (default: 1.0)."
    )

    # Optional flag to enable the Pygame visualizer.
    parser.add_argument(
        "--visualizer",
        action="store_true",
        help="Enable the graphical visualizer."
    )
    
    # Optional flag for verbose logging.
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug logging to the console."
    )

    args = parser.parse_args()

    # Validate arguments.
    if args.tps <= 0:
        parser.error("--tps must be a positive number.")

    # Set the global debug flag based on the parsed argument.
    config.DEBUG = args.debug

    return args


def debug_log(message: str, level: str = "info"):
    """
    Prints a message to the console if debug mode is enabled.

    Args:
        message (str): The message to log.
        level (str): The log level ('info', 'warning', 'error'). Affects the color.
    """
    if config.DEBUG:
        color_codes = {
            "info": "\033[94m",  # Blue
            "warning": "\033[93m", # Yellow
            "error": "\033[91m",   # Red
            "reset": "\033[0m"
        }
        color = color_codes.get(level.lower(), "")
        reset = color_codes["reset"] if color else ""
        print(f"{color}[DEBUG] {message}{reset}")
