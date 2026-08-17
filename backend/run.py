import sys
import argparse
import logging
from app.seeding import set_global_seed
from app.routes import app, init_traffic_manager

logger = logging.getLogger(__name__)


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="NexRoute Traffic Optimization Backend Server & Batch CLI"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="default",
        help="Scenario name to load from backend/scenarios/ (default: 'default')"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for Python, NumPy, and SUMO (default: None, random each run)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Force SUMO to launch in non-GUI mode (sumo binary instead of sumo-gui)"
    )
    parser.add_argument(
        "--mode",
        choices=["api", "batch"],
        default="api",
        help="Execution mode: 'api' to start Flask server or 'batch' for scripted execution (default: 'api')"
    )
    return parser.parse_args(args)


def main(args=None):
    parsed_args = parse_args(args)

    set_global_seed(parsed_args.seed)

    if parsed_args.mode == "batch":
        print("batch mode not yet implemented")
        sys.exit(0)

    init_traffic_manager(
        scenario_name=parsed_args.scenario,
        seed=parsed_args.seed,
        headless=parsed_args.headless
    )

    try:
        app.run(debug=True)
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
