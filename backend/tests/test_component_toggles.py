"""
Unit Tests for Independent Component Toggles (Signals / VSL / Routing).
Verifies zero computational overhead (skipped PSO calls and zero execution) when components are disabled.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.traffic_manager import AdvancedTrafficManager
from backend.app.routing_strategies import StaticRoutingStrategy, AdaptiveRoutingStrategy
from backend.app.scenario_loader import load_scenario
from backend.run import parse_args


def test_cli_component_toggle_flags():
    """Verify CLI parsing for --enable-signals, --enable-vsl, --enable-routing and --no-* flags."""
    # Default: all True
    args_default = parse_args([])
    assert args_default.enable_signals is True
    assert args_default.enable_vsl is True
    assert args_default.enable_routing is True

    # Disabling via --no-*
    args_disabled = parse_args(["--no-enable-signals", "--no-enable-vsl", "--no-enable-routing"])
    assert args_disabled.enable_signals is False
    assert args_disabled.enable_vsl is False
    assert args_disabled.enable_routing is False


def test_routing_reconciliation_when_routing_disabled(caplog):
    """Verify that when enable_routing=False, adaptive routing is overridden to StaticRoutingStrategy with a warning."""
    scen_cfg = load_scenario("default")

    with patch("backend.app.traffic_manager.set_global_seed"):
        tm = AdvancedTrafficManager(
            scenario_config=scen_cfg,
            enable_routing=False,
            routing_strategy="adaptive"
        )
        assert isinstance(tm.routing_strategy, StaticRoutingStrategy)
        assert "Routing is disabled (enable_routing=False)" in caplog.text


@patch("backend.app.traffic_manager.traci")
def test_component_toggles_zero_overhead_when_disabled(mock_traci):
    """
    Verify that when components are disabled, their _optimize_* wrapper methods
    AND underlying PSO optimization calls are NEVER executed (0 call count).
    """
    mock_traci.simulation.getTime.return_value = 1.0
    mock_traci.simulationStep.return_value = None
    mock_traci.vehicle.getIDList.return_value = []
    mock_traci.simulation.getMinExpectedNumber.return_value = 0

    scen_cfg = load_scenario("default")

    # Construct TrafficManager with all 3 subsystems DISABLED
    with patch("backend.app.traffic_manager.set_global_seed"):
        tm_disabled = AdvancedTrafficManager(
            scenario_config=scen_cfg,
            headless=True,
            enable_signals=False,
            enable_vsl=False,
            enable_routing=False
        )

    # Attach mock PSO optimizers
    mock_signal_pso = MagicMock()
    mock_speed_pso = MagicMock()
    mock_route_pso = MagicMock()
    tm_disabled.signal_pso = mock_signal_pso
    tm_disabled.speed_control_pso = mock_speed_pso
    tm_disabled.route_pso = mock_route_pso

    # Patch the _optimize_* wrapper methods
    with patch.object(tm_disabled, '_optimize_traffic_signals') as mock_opt_signals, \
         patch.object(tm_disabled, '_optimize_speed_limits') as mock_opt_vsl, \
         patch.object(tm_disabled, '_optimize_routing') as mock_opt_routing, \
         patch.object(tm_disabled, '_evaluate_system_performance', return_value={'avg_speed': 10}):

        tm_disabled.run_simulation(steps=1)

        # Assert wrappers were NEVER called
        assert mock_opt_signals.call_count == 0
        assert mock_opt_vsl.call_count == 0
        assert mock_opt_routing.call_count == 0

        # Assert underlying PSO iteration methods were NEVER called (zero computational overhead)
        assert mock_signal_pso.optimize.call_count == 0
        assert mock_speed_pso.optimize_step.call_count == 0
        assert mock_route_pso.optimize_step.call_count == 0


@patch("backend.app.traffic_manager.traci")
def test_component_toggles_execution_when_enabled(mock_traci):
    """Verify that when components are enabled, their optimization methods are called."""
    mock_traci.simulation.getTime.return_value = 1.0
    mock_traci.simulationStep.return_value = None
    mock_traci.vehicle.getIDList.return_value = []
    mock_traci.simulation.getMinExpectedNumber.return_value = 0

    scen_cfg = load_scenario("default")

    # Construct TrafficManager with all 3 subsystems ENABLED
    with patch("backend.app.traffic_manager.set_global_seed"):
        tm_enabled = AdvancedTrafficManager(
            scenario_config=scen_cfg,
            headless=True,
            enable_signals=True,
            enable_vsl=True,
            enable_routing=True
        )

    with patch.object(tm_enabled, '_optimize_traffic_signals') as mock_opt_signals, \
         patch.object(tm_enabled, '_optimize_speed_limits') as mock_opt_vsl, \
         patch.object(tm_enabled, '_optimize_routing') as mock_opt_routing, \
         patch.object(tm_enabled, '_evaluate_system_performance', return_value={'avg_speed': 10}):

        tm_enabled.run_simulation(steps=1)

        # Assert wrappers were called exactly once during optimization step 0
        assert mock_opt_signals.call_count == 1
        assert mock_opt_vsl.call_count == 1
        assert mock_opt_routing.call_count == 1
