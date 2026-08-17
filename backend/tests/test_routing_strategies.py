"""
Unit Tests for Routing Strategies (Static Baseline vs Adaptive Routing).
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.routing_strategies import (
    StaticRoutingStrategy,
    AdaptiveRoutingStrategy
)
from backend.app.traffic_manager import AdvancedTrafficManager
from backend.app.scenario_loader import load_scenario


def test_static_routing_strategy_weight_insensitivity():
    """Verify that StaticRoutingStrategy's edge weights are insensitive to congestion metrics."""
    strategy = StaticRoutingStrategy()
    edge_data = {'length': 500.0, 'speed': 10.0}

    # Low congestion metrics
    metrics_low = {
        'predicted_congestion': 0.1,
        'congestion_index': 0.1,
        'queue_length': 0,
        'avg_speed': 10.0,
        'stop_count': 0
    }

    # High congestion metrics
    metrics_high = {
        'predicted_congestion': 0.9,
        'congestion_index': 0.85,
        'queue_length': 15,
        'avg_speed': 1.5,
        'stop_count': 5
    }

    weight_low = strategy.compute_edge_weight("nodeA", "nodeB", edge_data, metrics_low)
    weight_high = strategy.compute_edge_weight("nodeA", "nodeB", edge_data, metrics_high)

    expected_static_weight = 500.0 / 10.0  # 50.0s free flow travel time

    assert weight_low == pytest.approx(expected_static_weight)
    assert weight_high == pytest.approx(expected_static_weight)
    assert weight_low == weight_high  # Insensitive to congestion!


def test_static_routing_strategy_should_reroute():
    """Verify that StaticRoutingStrategy always disables rerouting."""
    strategy = StaticRoutingStrategy()
    vehicle_state = {'speed': 0.0, 'waiting_time': 100, 'reroute_attempts': 0}
    traffic_metrics = {'edge1': {'predicted_congestion': 0.95}}

    assert strategy.should_reroute(vehicle_state, traffic_metrics) is False


def test_adaptive_routing_strategy_weight_sensitivity():
    """Verify that AdaptiveRoutingStrategy's edge weights change significantly with congestion."""
    strategy = AdaptiveRoutingStrategy(adaptive_routing_threshold=0.6)
    edge_data = {'length': 500.0, 'speed': 10.0}

    metrics_low = {
        'predicted_congestion': 0.1,
        'congestion_index': 0.1,
        'queue_length': 0,
        'avg_speed': 10.0,
        'stop_count': 0,
        'hist_congestion': 0.0
    }

    metrics_high = {
        'predicted_congestion': 0.8,  # > 0.6 threshold -> 5x multiplier
        'congestion_index': 0.8,
        'queue_length': 5,
        'avg_speed': 2.0,
        'stop_count': 2,
        'hist_congestion': 0.5
    }

    weight_low = strategy.compute_edge_weight("nodeA", "nodeB", edge_data, metrics_low)
    weight_high = strategy.compute_edge_weight("nodeA", "nodeB", edge_data, metrics_high)

    assert weight_high > weight_low * 5.0  # Significantly higher due to congestion and penalties!


def test_adaptive_routing_strategy_should_reroute():
    """Verify that AdaptiveRoutingStrategy enables rerouting when appropriate."""
    strategy = AdaptiveRoutingStrategy(adaptive_routing_threshold=0.6)

    # Stuck vehicle
    stuck_vehicle = {
        'speed': 0.0,
        'waiting_time': 45.0,
        'reroute_attempts': 0,
        'current_time': 100.0,
        'last_reroute_time': 0.0
    }
    assert strategy.should_reroute(stuck_vehicle) is True

    # Vehicle heading towards congested edge
    vehicle_heading_congestion = {
        'speed': 10.0,
        'waiting_time': 0.0,
        'reroute_attempts': 0,
        'current_time': 100.0,
        'last_reroute_time': 0.0,
        'upcoming_route': ['edge_congested']
    }
    metrics = {'edge_congested': {'predicted_congestion': 0.85}}
    assert strategy.should_reroute(vehicle_heading_congestion, metrics) is True


@patch("backend.app.traffic_manager.traci.start")
@patch("backend.app.traffic_manager.sumolib.net.readNet")
@patch("backend.app.traffic_manager.sumolib.checkBinary", return_value="sumo")
def test_traffic_manager_routing_strategy_initialization(mock_check_binary, mock_read_net, mock_traci_start):
    """Verify AdvancedTrafficManager initializes static vs adaptive routing strategies."""
    scen_cfg = load_scenario("default")

    tm_static = AdvancedTrafficManager(scenario_config=scen_cfg, routing_strategy="static", headless=True)
    assert isinstance(tm_static.routing_strategy, StaticRoutingStrategy)

    tm_adaptive = AdvancedTrafficManager(scenario_config=scen_cfg, routing_strategy="adaptive", headless=True)
    assert isinstance(tm_adaptive.routing_strategy, AdaptiveRoutingStrategy)
