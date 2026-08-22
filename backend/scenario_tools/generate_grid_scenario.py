"""
Synthetic Grid Network and Vehicle Demand Generator for SUMO.
Generates grid networks using SUMO's `netgenerate` and vehicle demand routes using `randomTrips.py`.
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path
import yaml

from backend.scenario_tools.demand_shapes import generate_demands_for_profile

logger = logging.getLogger(__name__)

# Demand level mapping to randomTrips period (seconds between vehicle departures).
# Reason for period values:
# - light: period = 2.0 (1800 vehicles/hour across network) - low density baseline testing
# - moderate: period = 1.0 (3600 vehicles/hour across network) - standard urban traffic density
# - heavy: period = 0.5 (7200 vehicles/hour across network) - high density inducing congestion/queues
DEMAND_PERIOD_MAP = {
    "light": 2.0,
    "moderate": 1.0,
    "heavy": 0.5
}


def locate_sumo_tools():
    """Verify SUMO_HOME environment variable and locate netgenerate & randomTrips.py."""
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        raise EnvironmentError(
            "SUMO_HOME environment variable is not set. "
            "Please set SUMO_HOME to your SUMO installation directory "
            "(e.g. C:\\Program Files (x86)\\Eclipse\\Sumo or /usr/share/sumo)."
        )

    sumo_home_path = Path(sumo_home)
    random_trips_py = sumo_home_path / "tools" / "randomTrips.py"
    if not random_trips_py.exists():
        raise FileNotFoundError(
            f"randomTrips.py not found at {random_trips_py}. Verify your SUMO installation."
        )

    # Locate netgenerate binary
    netgenerate_bin = sumo_home_path / "bin" / ("netgenerate.exe" if os.name == "nt" else "netgenerate")
    if not netgenerate_bin.exists():
        netgenerate_bin = "netgenerate"

    return sumo_home_path, netgenerate_bin, random_trips_py


def generate_grid_scenario(
    size: int = 5,
    length: float = 200.0,
    lanes: int = 2,
    demand_level: str = "moderate",
    demand_shape: str = "flat",
    output_dir: Path = None,
    seed: int = None
) -> Path:
    """Generate a synthetic grid network scenario with customizable demand shape profile."""
    sumo_home, netgenerate_bin, random_trips_py = locate_sumo_tools()

    scenario_name = f"grid_{size}_{demand_level}"
    if demand_shape != "flat":
        scenario_name = f"{scenario_name}_{demand_shape}"

    if output_dir is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
        output_dir = repo_root / "backend" / "scenarios" / scenario_name

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    net_file = output_dir / "grid.net.xml"
    route_file = output_dir / "grid.rou.xml"
    sumocfg_file = output_dir / "grid.sumocfg"
    scenario_yaml = output_dir / "scenario.yaml"

    # Step 1: Run netgenerate to build grid network
    netgenerate_cmd = [
        str(netgenerate_bin),
        "--grid",
        f"--grid.number={size}",
        f"--grid.length={length}",
        f"--default.lanenumber={lanes}",
        "--default.junctions.type", "traffic_light",
        "-o", str(net_file)
    ]
    logger.info(f"Generating grid network with netgenerate: size={size}x{size}, length={length}m, lanes={lanes}")
    res_net = subprocess.run(netgenerate_cmd, capture_output=True, text=True)
    if res_net.returncode != 0:
        raise RuntimeError(f"netgenerate failed:\n{res_net.stderr}")

    # Step 2: Generate vehicle demand profile routes using shared helper
    logger.info(f"Generating vehicle demand: level={demand_level}, shape={demand_shape}")
    generate_demands_for_profile(
        net_file=net_file,
        route_file=route_file,
        demand_level=demand_level,
        demand_shape=demand_shape,
        duration=3600.0,
        seed=seed,
        random_trips_py=random_trips_py
    )

    # Step 3: Write grid.sumocfg
    sumocfg_content = f"""<configuration>
    <input>
        <net-file value="grid.net.xml"/>
        <route-files value="grid.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>
"""
    sumocfg_file.write_text(sumocfg_content, encoding="utf-8")

    # Step 4: Write scenario.yaml
    scenario_dict = {
        "name": scenario_name,
        "sumo": {
            "gui": True,
            "config_file": "grid.sumocfg",
            "net_file": "grid.net.xml",
            "route_file": "grid.rou.xml"
        }
    }
    with open(scenario_yaml, "w", encoding="utf-8") as f:
        yaml.dump(scenario_dict, f, default_flow_style=False)

    logger.info(f"Successfully generated scenario '{scenario_name}' at {output_dir}")
    return output_dir


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Generate a synthetic grid network scenario for NexRoute"
    )
    parser.add_argument(
        "--size",
        type=int,
        default=5,
        help="Grid network dimension (e.g. 5 creates a 5x5 grid of junctions, default: 5)"
    )
    parser.add_argument(
        "--length",
        type=float,
        default=200.0,
        help="Length of each grid edge in meters (default: 200.0)"
    )
    parser.add_argument(
        "--lanes",
        type=int,
        default=2,
        help="Number of lanes per direction (default: 2)"
    )
    parser.add_argument(
        "--demand-level",
        type=str,
        choices=["light", "moderate", "heavy"],
        default="moderate",
        help="Vehicle demand level: 'light', 'moderate', or 'heavy' (default: 'moderate')"
    )
    parser.add_argument(
        "--demand-shape",
        type=str,
        choices=["flat", "single_peak", "two_peak"],
        default="flat",
        help="Vehicle demand profile shape: 'flat', 'single_peak', or 'two_peak' (default: 'flat')"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Target output directory (default: backend/scenarios/grid_{size}_{demand_level})"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible demand generation"
    )
    return parser.parse_args(args)


def main(args=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parsed = parse_args(args)
    generate_grid_scenario(
        size=parsed.size,
        length=parsed.length,
        lanes=parsed.lanes,
        demand_level=parsed.demand_level,
        demand_shape=parsed.demand_shape,
        output_dir=Path(parsed.output_dir) if parsed.output_dir else None,
        seed=parsed.seed
    )


if __name__ == "__main__":
    main()
