import os
import pytest
from pathlib import Path
from backend.app import config
from backend.app.scenario_loader import load_scenario, ScenarioConfig


def test_load_default_scenario():
    """Verify that default scenario loads correctly with valid absolute paths."""
    sc_config = load_scenario('default')
    assert isinstance(sc_config, ScenarioConfig)
    assert sc_config.name == 'default'
    assert sc_config.gui is True

    # Check sumo_config dictionary structure
    assert 'gui' in sc_config.sumo_config
    assert 'config_file' in sc_config.sumo_config
    assert 'net_file' in sc_config.sumo_config
    assert 'route_file' in sc_config.sumo_config

    # Check absolute paths
    assert os.path.isabs(sc_config.config_file)
    assert os.path.isabs(sc_config.net_file)
    assert os.path.isabs(sc_config.route_file)
    assert sc_config.config_file == sc_config.config_file_path
    assert sc_config.net_file == sc_config.net_file_path
    assert sc_config.route_file == sc_config.route_file_path
    assert sc_config.config_file.endswith('broh.sumocfg')
    assert sc_config.net_file.endswith('broh.net.xml')
    assert sc_config.route_file.endswith('broh.rou.xml')

    # Check default constants
    assert sc_config.OPTIMIZATION_INTERVAL == config.OPTIMIZATION_INTERVAL
    assert sc_config.optimization_interval == config.OPTIMIZATION_INTERVAL
    assert sc_config.SPEED_LIMITS == config.SPEED_LIMITS


def test_missing_scenario_raises_clear_error():
    """Verify that attempting to load a non-existent scenario raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_scenario('non_existent_scenario_xyz')

    assert "non_existent_scenario_xyz" in str(exc_info.value)


def test_relative_paths_resolve_independently_of_cwd(tmp_path, monkeypatch):
    """Verify relative paths resolve to absolute scenario paths regardless of CWD."""
    scenarios_dir = tmp_path / "scenarios"
    scen_dir = scenarios_dir / "test_cwd"
    scen_dir.mkdir(parents=True)

    yaml_content = (
        "name: test_cwd\n"
        "sumo:\n"
        "  gui: true\n"
        "  config_file: rel/path/test.sumocfg\n"
        "  net_file: test.net.xml\n"
        "  route_file: test.rou.xml\n"
    )
    (scen_dir / "scenario.yaml").write_text(yaml_content)

    # Change current working directory to an unrelated temporary directory
    other_dir = tmp_path / "unrelated_working_dir"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    sc_config = load_scenario('test_cwd', scenarios_dir=scenarios_dir)

    expected_net_path = str((scen_dir / "test.net.xml").resolve())
    expected_cfg_path = str((scen_dir / "rel/path/test.sumocfg").resolve())

    assert os.path.isabs(sc_config.net_file)
    assert os.path.isabs(sc_config.config_file)
    assert sc_config.net_file == expected_net_path
    assert sc_config.config_file == expected_cfg_path


def test_nested_dictionary_deep_merge_overrides(tmp_path):
    """Verify recursive deep merging of nested dictionary overrides on top of defaults."""
    scenarios_dir = tmp_path / "scenarios"
    scen_dir = scenarios_dir / "deep_override"
    scen_dir.mkdir(parents=True)

    yaml_content = (
        "name: deep_override\n"
        "sumo:\n"
        "  gui: false\n"
        "  config_file: sim.sumocfg\n"
        "  net_file: sim.net.xml\n"
        "  route_file: sim.rou.xml\n"
        "optimization_interval: 50\n"
        "pso_particles: 25\n"
        "speed_limits:\n"
        "  urban: 12.5\n"
    )
    (scen_dir / "scenario.yaml").write_text(yaml_content)

    sc_config = load_scenario('deep_override', scenarios_dir=scenarios_dir)

    # Check scalar overrides
    assert sc_config.gui is False
    assert sc_config.OPTIMIZATION_INTERVAL == 50
    assert sc_config.pso_particles == 25

    # Check deep dictionary merge: 'urban' updated, other keys retained from config defaults
    assert sc_config.SPEED_LIMITS['urban'] == 12.5
    assert sc_config.SPEED_LIMITS['arterial'] == config.SPEED_LIMITS['arterial']
    assert sc_config.SPEED_LIMITS['highway'] == config.SPEED_LIMITS['highway']
    assert sc_config.CONGESTION_THRESHOLDS == config.CONGESTION_THRESHOLDS


def test_unknown_keys_rejected(tmp_path):
    """Verify that unknown/invalid keys in scenario YAML raise ValueError."""
    scenarios_dir = tmp_path / "scenarios"
    scen_dir = scenarios_dir / "invalid_key_scen"
    scen_dir.mkdir(parents=True)

    yaml_content = (
        "name: invalid_key_scen\n"
        "sumo:\n"
        "  config_file: sim.sumocfg\n"
        "  net_file: sim.net.xml\n"
        "  route_file: sim.rou.xml\n"
        "unknown_parameter_name: 123\n"
    )
    (scen_dir / "scenario.yaml").write_text(yaml_content)

    with pytest.raises(ValueError) as exc_info:
        load_scenario('invalid_key_scen', scenarios_dir=scenarios_dir)

    assert "Unknown key" in str(exc_info.value)
    assert "unknown_parameter_name" in str(exc_info.value)


def test_malformed_yaml_raises_error(tmp_path):
    """Verify that malformed YAML syntax raises ValueError."""
    scenarios_dir = tmp_path / "scenarios"
    scen_dir = scenarios_dir / "malformed_scen"
    scen_dir.mkdir(parents=True)

    yaml_content = "name: malformed\nsumo: [unclosed_list"
    (scen_dir / "scenario.yaml").write_text(yaml_content)

    with pytest.raises(ValueError) as exc_info:
        load_scenario('malformed_scen', scenarios_dir=scenarios_dir)

    assert "Malformed YAML" in str(exc_info.value)
