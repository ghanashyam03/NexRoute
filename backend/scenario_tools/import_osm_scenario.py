"""
Real-World OpenStreetMap (OSM) Road Network Import Pipeline for SUMO / NexRoute.
Imports raw .osm / .osm.xml extracts into SUMO .net.xml networks using `netconvert`,
generates vehicle demand using `randomTrips.py`, and registers scenario definitions.
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

logger = logging.getLogger(__name__)

# Demand level mapping to randomTrips period (seconds between vehicle departures).
# Relative demand rates mapping:
# - light: period = 2.0 (0.5 veh/sec = 1,800 veh/hr rate) - low density baseline for OSM networks
# - moderate: period = 1.0 (1.0 veh/sec = 3,600 veh/hr rate) - standard urban traffic load
# - heavy: period = 0.5 (2.0 veh/sec = 7,200 veh/hr rate) - heavy urban congestion & queueing
DEMAND_PERIOD_MAP = {
    "light": 2.0,
    "moderate": 1.0,
    "heavy": 0.5
}


def locate_sumo_tools():
    """Verify SUMO_HOME environment variable and locate netconvert & randomTrips.py."""
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

    netconvert_bin = sumo_home_path / "bin" / ("netconvert.exe" if os.name == "nt" else "netconvert")
    if not netconvert_bin.exists():
        netconvert_bin = "netconvert"

    return sumo_home_path, netconvert_bin, random_trips_py


def validate_osm_input(osm_file_path: Path):
    """Pre-validation check on user-supplied OSM file."""
    if not osm_file_path.exists():
        raise FileNotFoundError(f"OSM file not found at: {osm_file_path}")

    file_size = osm_file_path.stat().st_size
    if file_size < 100:
        raise ValueError(f"OSM file at '{osm_file_path}' is empty or too small ({file_size} bytes) to contain road data.")

    if file_size < 1024:
        logger.warning(
            f"OSM file at '{osm_file_path}' is suspiciously small ({file_size} bytes < 1KB). "
            "OpenStreetMap export may have failed or contain no road ways."
        )


def validate_generated_network(net_file_path: Path):
    """Post-validation check to verify netconvert generated valid edges and junctions."""
    if not net_file_path.exists():
        raise RuntimeError(f"Generated network file missing at {net_file_path}")

    try:
        tree = ET.parse(net_file_path)
        root = tree.getroot()

        # Check for edges (excluding internal function edges)
        edges = [e for e in root.findall("edge") if not e.attrib.get("function") == "internal"]
        junctions = [j for j in root.findall("junction") if j.attrib.get("type") != "internal"]

        if len(edges) == 0:
            raise ValueError(f"netconvert produced network at '{net_file_path}' with 0 valid road edges.")

        if len(junctions) == 0:
            raise ValueError(f"netconvert produced network at '{net_file_path}' with 0 junctions.")

        logger.info(f"Validated network '{net_file_path.name}': {len(edges)} edges, {len(junctions)} junctions.")

    except ET.ParseError as err:
        raise RuntimeError(f"Generated network file '{net_file_path}' is invalid XML: {err}")


def import_osm_scenario(
    osm_file: Path,
    scenario_name: str = None,
    demand_level: str = "moderate",
    output_dir: Path = None,
    seed: int = None
) -> Path:
    """Import an OpenStreetMap .osm file and build a complete loadable SUMO scenario."""
    osm_path = Path(osm_file).resolve()
    validate_osm_input(osm_path)

    if demand_level not in DEMAND_PERIOD_MAP:
        raise ValueError(f"Invalid demand_level '{demand_level}'. Must be one of {list(DEMAND_PERIOD_MAP.keys())}")

    sumo_home, netconvert_bin, random_trips_py = locate_sumo_tools()

    if scenario_name is None:
        clean_stem = osm_path.stem.replace(".", "_")
        scenario_name = f"osm_{clean_stem}"

    if output_dir is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
        output_dir = repo_root / "backend" / "scenarios" / scenario_name

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    net_file = output_dir / "osm.net.xml"
    route_file = output_dir / "osm.rou.xml"
    sumocfg_file = output_dir / "osm.sumocfg"
    scenario_yaml = output_dir / "scenario.yaml"

    # Selected netconvert flags and technical rationale for OSM road network import:
    # --osm-files: specifies the raw input OpenStreetMap XML extract file.
    # --output-file: specifies target SUMO network file (.net.xml).
    # --geometry.remove: simplifies edge geometries by removing collinear intermediate shape nodes without altering topology.
    # --ramps.guess: enables automatic identification and geometric modeling of highway on/off ramps.
    # --junctions.join: merges close adjacent nodes into unified complex junctions (improves realistic traffic light modeling).
    # --tls.discard-simple: strips traffic lights placed on simple non-intersection nodes to avoid unnecessary stops.
    # --tls.join: groups traffic signals belonging to the same physical intersection under unified controllers.
    # --tls.guess-signals: infers traffic signal positions for major urban intersections when OSM signal tags are incomplete.
    # --remove-edges.isolated: prunes disconnected road fragments that cannot reach or be reached by the main network graph.
    netconvert_cmd = [
        str(netconvert_bin),
        "--osm-files", str(osm_path),
        "--output-file", str(net_file),
        "--geometry.remove",
        "--ramps.guess",
        "--junctions.join",
        "--tls.discard-simple",
        "--tls.join",
        "--tls.guess-signals",
        "--remove-edges.isolated"
    ]

    logger.info(f"Running netconvert on '{osm_path.name}' -> '{net_file.name}'...")
    res_net = subprocess.run(netconvert_cmd, capture_output=True, text=True)
    if res_net.returncode != 0:
        raise RuntimeError(f"netconvert failed for '{osm_path}':\n{res_net.stderr}")

    # Post-validation check
    validate_generated_network(net_file)

    # Vehicle demand generation via randomTrips.py
    period = DEMAND_PERIOD_MAP[demand_level]
    random_trips_cmd = [
        sys.executable,
        str(random_trips_py),
        "-n", str(net_file),
        "-r", str(route_file),
        "-e", "3600",
        "-p", str(period),
        "--fringe-junctions",
        "--validate"
    ]
    if seed is not None:
        random_trips_cmd.extend(["-s", str(seed)])

    logger.info(f"Generating demand with randomTrips.py: demand_level={demand_level} (period={period}s)...")
    res_trips = subprocess.run(random_trips_cmd, capture_output=True, text=True)
    if res_trips.returncode != 0:
        raise RuntimeError(f"randomTrips.py failed for network '{net_file}':\n{res_trips.stderr}")

    # Write osm.sumocfg
    sumocfg_content = f"""<configuration>
    <input>
        <net-file value="osm.net.xml"/>
        <route-files value="osm.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>
"""
    sumocfg_file.write_text(sumocfg_content, encoding="utf-8")

    # Write scenario.yaml
    scenario_dict = {
        "name": scenario_name,
        "sumo": {
            "gui": True,
            "config_file": "osm.sumocfg",
            "net_file": "osm.net.xml",
            "route_file": "osm.rou.xml"
        }
    }
    with open(scenario_yaml, "w", encoding="utf-8") as f:
        yaml.dump(scenario_dict, f, default_flow_style=False)

    logger.info(f"Successfully imported OSM scenario '{scenario_name}' at {output_dir}")
    return output_dir


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Import an OpenStreetMap (.osm) extract into a loadable NexRoute scenario"
    )
    parser.add_argument(
        "--osm-file",
        type=str,
        required=True,
        help="Path to user-supplied raw OpenStreetMap XML file (.osm / .osm.xml)"
    )
    parser.add_argument(
        "--scenario-name",
        type=str,
        default=None,
        help="Target scenario name (default: derived from osm file stem)"
    )
    parser.add_argument(
        "--demand-level",
        type=str,
        choices=["light", "moderate", "heavy"],
        default="moderate",
        help="Vehicle demand level: 'light' (period=2.0s), 'moderate' (period=1.0s), or 'heavy' (period=0.5s) (default: 'moderate')"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Target output directory (default: backend/scenarios/<scenario_name>)"
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
    import_osm_scenario(
        osm_file=Path(parsed.osm_file),
        scenario_name=parsed.scenario_name,
        demand_level=parsed.demand_level,
        output_dir=Path(parsed.output_dir) if parsed.output_dir else None,
        seed=parsed.seed
    )


if __name__ == "__main__":
    main()
