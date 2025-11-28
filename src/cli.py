import argparse
import config


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the simulation.

    Return: Parsed arguments containing:
            - map: Path to the map file (required)
            - tps: Ticks per second (optional, default=1)
            - max_ticks: Maximum number of ticks (optional, default=2000)
            - debug: Enable debug logging (optional, default=False)
    """
    parser = argparse.ArgumentParser(
        description="Run a cellular automaton traffic simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --map data/city.map
  python main.py --map data/city.map --tps 1.0 --max-ticks 100
  python main.py --map data/city.map --debug
        """
    )

    parser.add_argument(
        "--map",
        type=str,
        required=True,
        help="Path to the map file (required)"
    )

    # Optional arguments
    parser.add_argument(
        "--tps",
        type=float,
        default=1,
        help="Ticks per second (default: 1, must be > 0)"
    )

    parser.add_argument(
        "--max-ticks",
        type=int,
        default=2000,
        help="Maximum number of ticks to simulate (default: 2000, must be > 0)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.tps <= 0:
        parser.error("--tps must be greater than 0")

    if args.max_ticks <= 0:
        parser.error("--max-ticks must be greater than 0")

    config.DEBUG = args.debug

    return args


def debug_log(message: str, end="\n"):
    """
    Print a debug message if debug mode is enabled.
    :param message: The message to log
    :param end: The end of the message, by default a newline character
    """
    if config.DEBUG:
        print(f"{message}", end=end)
