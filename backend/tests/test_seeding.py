import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from backend.app.seeding import set_global_seed
from backend.app.optimizer import ParticleSwarmOptimizer
from backend.app.traffic_manager import AdvancedTrafficManager
from backend.app.scenario_loader import ScenarioConfig


def dummy_objective(position: np.ndarray) -> float:
    """Simple deterministic sphere objective function."""
    return float(np.sum((position - 1.5) ** 2))


def test_set_global_seed_reproducibility():
    """Verify that using the same global seed produces bit-for-bit identical PSO results."""
    bounds = [(-10.0, 10.0)] * 3

    set_global_seed(42)
    pso1 = ParticleSwarmOptimizer(
        num_particles=15,
        num_dimensions=3,
        bounds=bounds,
        objective_function=dummy_objective,
        max_iterations=20
    )
    best_pos1, best_score1 = pso1.optimize()

    set_global_seed(42)
    pso2 = ParticleSwarmOptimizer(
        num_particles=15,
        num_dimensions=3,
        bounds=bounds,
        objective_function=dummy_objective,
        max_iterations=20
    )
    best_pos2, best_score2 = pso2.optimize()

    np.testing.assert_array_equal(best_pos1, best_pos2)
    assert best_score1 == best_score2


def test_unseeded_runs_are_nondeterministic():
    """Verify that unseeded runs (seed=None) produce differing positions across runs."""
    bounds = [(-100.0, 100.0)] * 5

    # Note: Flake risk on random floats matching across separate unseeded runs is extremely low (< 1e-15)
    set_global_seed(None)
    pso1 = ParticleSwarmOptimizer(
        num_particles=20,
        num_dimensions=5,
        bounds=bounds,
        objective_function=dummy_objective,
        max_iterations=10
    )
    best_pos1, _ = pso1.optimize()

    set_global_seed(None)
    pso2 = ParticleSwarmOptimizer(
        num_particles=20,
        num_dimensions=5,
        bounds=bounds,
        objective_function=dummy_objective,
        max_iterations=10
    )
    best_pos2, _ = pso2.optimize()

    assert not np.allclose(best_pos1, best_pos2)


@patch("backend.app.traffic_manager.traci.start")
@patch("backend.app.traffic_manager.sumolib.net.readNet")
@patch("backend.app.traffic_manager.sumolib.checkBinary", return_value="sumo")
def test_traffic_manager_sumo_cmd_seed_flag(mock_check_binary, mock_read_net, mock_traci_start):
    """Verify that AdvancedTrafficManager passes --seed when seed is set, and --random when seed is None."""
    from backend.app.scenario_loader import load_scenario
    scen_cfg = load_scenario("default")

    # Test with seed
    tm_seeded = AdvancedTrafficManager(scenario_config=scen_cfg, seed=123, headless=True)
    tm_seeded.start_simulation()
    cmd_seeded = mock_traci_start.call_args[0][0]
    assert '--seed' in cmd_seeded
    assert cmd_seeded[cmd_seeded.index('--seed') + 1] == '123'
    assert '--random' not in cmd_seeded

    mock_traci_start.reset_mock()

    # Test without seed (nondeterministic)
    tm_unseeded = AdvancedTrafficManager(scenario_config=scen_cfg, seed=None, headless=True)
    tm_unseeded.start_simulation()
    cmd_unseeded = mock_traci_start.call_args[0][0]
    assert '--random' in cmd_unseeded
    assert '--seed' not in cmd_unseeded
