"""
Unit tests for OpenStreetMap (OSM) import pipeline.
"""

import os
import pytest
from pathlib import Path
import yaml
from backend.scenario_tools.import_osm_scenario import (
    import_osm_scenario,
    locate_sumo_tools,
    validate_osm_input
)
from backend.app.scenario_loader import load_scenario


def is_sumo_available():
    """Check if SUMO_HOME is configured and tools are reachable."""
    try:
        locate_sumo_tools()
        return True
    except (EnvironmentError, FileNotFoundError):
        return False


def get_fixture_osm():
    """Return Path to minimal_sample.osm fixture."""
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "minimal_sample.osm"
    return fixture_path


@pytest.mark.skipif(not is_sumo_available(), reason="SUMO_HOME is not set or netconvert/randomTrips.py is unavailable.")
def test_import_osm_scenario_end_to_end(tmp_path):
    """Verify that importing minimal_sample.osm generates net, route, sumocfg, and loadable scenario.yaml."""
    osm_fixture = get_fixture_osm()
    assert osm_fixture.exists()

    output_dir = tmp_path / "osm_sample_test"

    res_path = import_osm_scenario(
        osm_file=osm_fixture,
        scenario_name="osm_sample_test",
        demand_level="light",
        output_dir=output_dir,
        seed=42
    )

    assert res_path == output_dir
    assert (output_dir / "osm.net.xml").exists()
    assert (output_dir / "osm.rou.xml").exists()
    assert (output_dir / "osm.sumocfg").exists()

    scenario_yaml = output_dir / "scenario.yaml"
    assert scenario_yaml.exists()

    with open(scenario_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "osm_sample_test"
    assert data["sumo"]["config_file"] == "osm.sumocfg"
    assert data["sumo"]["net_file"] == "osm.net.xml"
    assert data["sumo"]["route_file"] == "osm.rou.xml"

    # Verify load_scenario works with the imported scenario
    config = load_scenario("osm_sample_test", scenarios_dir=tmp_path)
    assert config.name == "osm_sample_test"
    assert Path(config.net_file).exists()
    assert Path(config.route_file).exists()


def test_import_osm_pre_validation_checks(tmp_path):
    """Verify pre-validation checks catch non-existent or empty OSM files."""
    missing_file = tmp_path / "non_existent.osm"
    with pytest.raises(FileNotFoundError):
        validate_osm_input(missing_file)

    empty_file = tmp_path / "empty.osm"
    empty_file.write_text("<osm></osm>", encoding="utf-8")  # < 100 bytes
    with pytest.raises(ValueError):
        validate_osm_input(empty_file)
