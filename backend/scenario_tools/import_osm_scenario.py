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

from backend.scenario_tools.demand_shapes import generate_demands_for_profile

logger = logging.getLogger(__name__)


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
    demand_shape: str = "flat",
    output_dir: Path = None,
    seed: int = None
) -> Path:
    """Import an OpenStreetMap .osm file and build a complete loadable SUMO scenario."""
    osm_path = Path(osm_file).resolve()
    validate_osm_input(osm_path)

    sumo_home, netconvert_bin, random_trips_py = locate_sumo_tools()

    if scenario_name is None:
        clean_stem = osm_path.stem.replace(".", "_")
        scenario_name = f"osm_{clean_stem}"
        if demand_shape != "flat":
            scenario_name = f"{scenario_name}_{demand_shape}"

    if output_dir is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
        output_dir = repo_root / "backend" / "scenarios" / scenario_name

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    net_file = output_dir / "osm.net.xml"
    route_file = output_dir / "osm.rou.xml"
    sumocfg_file = output_dir / "osm.sumocfg"
    scenario_yaml = output_dir / "scenario.yaml"

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

    # Vehicle demand generation via demand_shapes helper
    logger.info(f"Generating demand profile routes: level={demand_level}, shape={demand_shape}...")
    generate_demands_for_profile(
        net_file=net_file,
        route_file=route_file,
        demand_level=demand_level,
        demand_shape=demand_shape,
        duration=3600.0,
        seed=seed,
        random_trips_py=random_trips_py
    )

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
        demand_shape=parsed.demand_shape,
        output_dir=Path(parsed.output_dir) if parsed.output_dir else None,
        seed=parsed.seed
    )


if __name__ == "__main__":
    main()
