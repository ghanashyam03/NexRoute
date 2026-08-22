"""
Unit tests for synthetic grid network and demand generator.
"""

import os
import pytest
from pathlib import Path
import yaml
from backend.scenario_tools.generate_grid_scenario import generate_grid_scenario, locate_sumo_tools
from backend.app.scenario_loader import load_scenario


def is_sumo_available():
    """Check if SUMO_HOME is set and tools are reachable."""
    try:
        locate_sumo_tools()
        return True
    except (EnvironmentError, FileNotFoundError):
        return False


@pytest.mark.skipif(not is_sumo_available(), reason="SUMO_HOME environment variable is not set or SUMO tools are missing.")
def test_generate_grid_scenario_creates_expected_files(tmp_path):
    """Verify generate_grid_scenario generates net, route, sumocfg, and scenario.yaml files for a tiny grid (size 2)."""
    output_dir = tmp_path / "grid_2_light"

    res_path = generate_grid_scenario(
        size=2,
        length=100.0,
        lanes=1,
        demand_level="light",
        output_dir=output_dir,
        seed=123
    )

    assert res_path == output_dir
    assert (output_dir / "grid.net.xml").exists()
    assert (output_dir / "grid.rou.xml").exists()
    assert (output_dir / "grid.sumocfg").exists()

    scenario_yaml = output_dir / "scenario.yaml"
    assert scenario_yaml.exists()

    with open(scenario_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "grid_2_light"
    assert data["sumo"]["config_file"] == "grid.sumocfg"
    assert data["sumo"]["net_file"] == "grid.net.xml"
    assert data["sumo"]["route_file"] == "grid.rou.xml"


@pytest.mark.skipif(not is_sumo_available(), reason="SUMO_HOME environment variable is not set or SUMO tools are missing.")
def test_generated_scenario_is_loadable_by_scenario_loader(tmp_path):
    """Verify that a generated grid scenario is cleanly loadable via load_scenario()."""
    output_dir = tmp_path / "grid_2_moderate"

    generate_grid_scenario(
        size=2,
        length=100.0,
        lanes=1,
        demand_level="moderate",
        output_dir=output_dir,
        seed=456
    )

    config = load_scenario("grid_2_moderate", scenarios_dir=tmp_path)
    assert config.name == "grid_2_moderate"
    assert Path(config.net_file).exists()
    assert Path(config.route_file).exists()
