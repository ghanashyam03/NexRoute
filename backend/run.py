import sys
import json
import argparse
import logging
import traceback
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
        "--steps",
        type=int,
        default=3600,
        help="Number of simulation steps to run in batch mode (default: 3600)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Output directory path for storing run metrics (default: 'results')"
    )
    parser.add_argument(
        "--mode",
        choices=["api", "batch"],
        default="api",
        help="Execution mode: 'api' to start Flask server or 'batch' for scripted execution (default: 'api')"
    )
    parser.add_argument(
        "--congestion-weights",
        type=str,
        default=None,
        help="Comma-separated 7 float values for congestion prediction weight vector override"
    )
    parser.add_argument(
        "--vsl-signal-aware",
        action="store_true",
        default=False,
        help="Enable green-phase speed bypass guard for VSL"
    )
    parser.add_argument(
        "--vsl-min-speed",
        type=float,
        default=5.0,
        help="Minimum speed limit floor for VSL speed harmonization (default: 5.0 m/s)"
    )
    parser.add_argument(
        "--routing-threshold",
        type=float,
        default=0.65,
        help="Congestion index threshold (C_pred) for dynamic rerouting activation (default: 0.65)"
    )
    return parser.parse_args(args)


def run_batch_mode(parsed_args):
    """Execute a batch simulation run end-to-end without starting Flask API server."""
    try:
        set_global_seed(parsed_args.seed)

        tm = init_traffic_manager(
            scenario_name=parsed_args.scenario,
            seed=parsed_args.seed,
            headless=parsed_args.headless,
            output_dir=parsed_args.output_dir,
            signal_strategy=parsed_args.signal_strategy,
            routing_strategy=parsed_args.routing_strategy,
            enable_signals=parsed_args.enable_signals,
            enable_vsl=parsed_args.enable_vsl,
            enable_routing=parsed_args.enable_routing,
            vsl_signal_aware=parsed_args.vsl_signal_aware,
            vsl_min_speed=parsed_args.vsl_min_speed,
            routing_threshold=parsed_args.routing_threshold
        )

        if getattr(parsed_args, 'congestion_weights', None):
            raw_w = [float(x.strip()) for x in parsed_args.congestion_weights.split(",")]
            from app.congestion_weight_search import normalize_weights
            tm.congestion_weights = normalize_weights(raw_w)

        tm.run_batch_simulation(steps=parsed_args.steps)

        run_id = tm.metrics_logger.run_id
        summary_file = tm.metrics_logger.json_path

        final_metrics = {}
        if summary_file.exists():
            with open(summary_file, "r", encoding="utf-8") as f:
                file_summary = json.load(f)
                final_metrics = file_summary.get("summary_metrics", {})

        summary_data = {
            "run_id": run_id,
            "scenario": parsed_args.scenario,
            "seed": parsed_args.seed,
            "enabled_components": {
                "signals": parsed_args.enable_signals,
                "vsl": parsed_args.enable_vsl,
                "routing": parsed_args.enable_routing
            },
            "signal_strategy": parsed_args.signal_strategy,
            "routing_strategy": str(tm.routing_strategy.__class__.__name__),
            "final_metrics": final_metrics,
            "summary_file": str(summary_file),
            "timeseries_file": str(tm.metrics_logger.csv_path)
        }

        print(json.dumps(summary_data))
        return summary_data

    except Exception as e:
        logger.error(f"Batch mode simulation failed: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)


def main(args=None):
    parsed_args = parse_args(args)

    set_global_seed(parsed_args.seed)

    if parsed_args.mode == "batch":
        run_batch_mode(parsed_args)
        sys.exit(0)

    init_traffic_manager(
        scenario_name=parsed_args.scenario,
        seed=parsed_args.seed,
        headless=parsed_args.headless,
        output_dir=parsed_args.output_dir,
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
