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
        "--signal-strategy",
        type=str,
        choices=["pso", "webster"],
        default="pso",
        help="Signal control strategy: 'pso' for adaptive PSO tuning or 'webster' for fixed-time Webster baseline (default: 'pso')"
    )
    parser.add_argument(
        "--routing-strategy",
        type=str,
        choices=["static", "adaptive"],
        default="adaptive",
        help="Routing strategy: 'static' for fixed shortest path or 'adaptive' for dynamic PSO rerouting (default: 'adaptive')"
    )
    parser.add_argument(
        "--enable-signals",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable traffic signal optimization subsystem (default: --enable-signals)"
    )
    parser.add_argument(
        "--enable-vsl",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable Variable Speed Limit (VSL) subsystem (default: --enable-vsl)"
    )
    parser.add_argument(
        "--enable-routing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable dynamic routing subsystem (default: --enable-routing)"
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
        headless=parsed_args.headless,
        signal_strategy=parsed_args.signal_strategy,
        routing_strategy=parsed_args.routing_strategy,
        enable_signals=parsed_args.enable_signals,
        enable_vsl=parsed_args.enable_vsl,
        enable_routing=parsed_args.enable_routing
    )

    try:
        app.run(debug=True)
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
