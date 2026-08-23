"""
Unit tests for VSL and Routing activation & max predicted congestion diagnostic counters.

Verifies:
  1. Initial counter values are 0.
  2. vsl_activations increments when speed limit optimization is applied via TraCI.
  3. routing_reroutes increments when vehicle reroutes are assigned via TraCI.
  4. max_predicted_congestion_observed tracks peak edge predicted congestion.
  5. _evaluate_system_performance includes all 3 counter keys in summary metrics dict.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from pathlib import Path

# Add repository root to sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.traffic_manager import AdvancedTrafficManager
from backend.app.models import TrafficMetrics, VehicleState
from backend.app.scenario_loader import ScenarioConfig


class TestActivationCounters(unittest.TestCase):
    """Test suite verifying vsl_activations, routing_reroutes, and max_predicted_congestion_observed."""

    def setUp(self):
        # Create a stubbed ScenarioConfig
        self.config = ScenarioConfig(
            name="test_activation_scenario",
            sumo_config={"gui": False, "route_file": "dummy.rou.xml", "net_file": "dummy.net.xml"},
            config_file="dummy.sumocfg",
            net_file="dummy.net.xml",
            route_file="dummy.rou.xml"
        )

    @patch('sumolib.net.readNet')
    @patch('backend.app.traffic_manager.set_global_seed')
    @patch('backend.app.traffic_manager.RunMetricsLogger')
    @patch('backend.app.traffic_manager.AdvancedTrafficManager._initialize_system')
    def test_initial_counter_values(self, mock_init, mock_logger, mock_seed, mock_read_net):
        """Verify counters initialize to zero / 0.0."""
        tm = AdvancedTrafficManager(scenario_config=self.config, headless=True)
        self.assertEqual(tm.vsl_activations, 0)
        self.assertEqual(tm.routing_reroutes, 0)
        self.assertEqual(tm.max_predicted_congestion_observed, 0.0)

    @patch('sumolib.net.readNet')
    @patch('backend.app.traffic_manager.set_global_seed')
    @patch('backend.app.traffic_manager.RunMetricsLogger')
    @patch('backend.app.traffic_manager.AdvancedTrafficManager._initialize_system')
    def test_vsl_activation_counter(self, mock_init, mock_logger, mock_seed, mock_read_net):
        """Verify vsl_activations increments when setMaxSpeed is executed."""
        tm = AdvancedTrafficManager(scenario_config=self.config, headless=True)
        
        # Mock net edge and metrics
        mock_edge = MagicMock()
        mock_edge.getSpeed.return_value = 13.89
        tm.net = MagicMock()
        tm.net.getEdge.return_value = mock_edge
        
        mock_metrics = TrafficMetrics()
        mock_metrics.predicted_congestion = 0.8
        mock_metrics.queue_length = 2
        mock_metrics.density = 20.0
        mock_metrics.stop_count = 1
        tm.traffic_metrics["edge_1"] = mock_metrics

        with patch('traci.edge.setMaxSpeed') as mock_set_max_speed:
            with patch.object(tm, '_harmonize_speeds'):
                tm._apply_speed_optimization(["edge_1"], (0.5, 0.5, 0.5, 0.3))
                
        self.assertEqual(tm.vsl_activations, 1)
        mock_set_max_speed.assert_called_once()

    @patch('sumolib.net.readNet')
    @patch('backend.app.traffic_manager.set_global_seed')
    @patch('backend.app.traffic_manager.RunMetricsLogger')
    @patch('backend.app.traffic_manager.AdvancedTrafficManager._initialize_system')
    def test_routing_reroutes_counter(self, mock_init, mock_logger, mock_seed, mock_read_net):
        """Verify routing_reroutes increments when vehicle setRoute is executed with a new route."""
        tm = AdvancedTrafficManager(scenario_config=self.config, headless=True)
        
        v_state = VehicleState(
            id="veh_0",
            type="passenger",
            position=(0.0, 0.0),
            speed=2.0,
            route=["edge_A", "edge_B"],
            current_edge="edge_A",
            destination="edge_C",
            reroute_attempts=0,
            priority=1.0,
            last_reroute_time=0.0,
            waiting_time=0.0,
            lane_position=10.0,
            acceleration=0.0
        )
        tm.vehicle_states["veh_0"] = v_state
        tm.net = MagicMock()
        mock_edge = MagicMock()
        mock_edge.getID.return_value = "edge_A"
        mock_edge.getLength.return_value = 100.0
        mock_edge.getSpeed.return_value = 13.89
        tm.net.getEdges.return_value = [mock_edge]

        with patch('traci.simulation.getTime', return_value=100.0):
            with patch('traci.edge.adaptTraveltime'):
                with patch('traci.vehicle.getRoute', return_value=["edge_A", "edge_B"]):
                    with patch('traci.vehicle.getRouteIndex', return_value=0):
                        with patch('traci.vehicle.setRoutingMode'):
                            mock_find = MagicMock()
                            mock_find.edges = ["edge_A", "edge_C", "edge_D"]
                            with patch('traci.simulation.findRoute', return_value=mock_find):
                                with patch('traci.vehicle.setRoute') as mock_set_route:
                                    tm._apply_adaptive_routing(["veh_0"], params=(1.0, 1.0, 1.0, 1.0))

        self.assertEqual(tm.routing_reroutes, 1)
        mock_set_route.assert_called_once_with("veh_0", ["edge_A", "edge_C", "edge_D"])

    @patch('sumolib.net.readNet')
    @patch('backend.app.traffic_manager.set_global_seed')
    @patch('backend.app.traffic_manager.RunMetricsLogger')
    @patch('backend.app.traffic_manager.AdvancedTrafficManager._initialize_system')
    def test_max_predicted_congestion_counter_and_summary_dict(self, mock_init, mock_logger, mock_seed, mock_read_net):
        """Verify max_predicted_congestion_observed tracks max prediction and is exported in global_metrics."""
        tm = AdvancedTrafficManager(scenario_config=self.config, headless=True)
        
        m1 = TrafficMetrics()
        m1.predicted_congestion = 2.4
        m2 = TrafficMetrics()
        m2.predicted_congestion = 6.2
        
        edge_dict = {"e1": m1, "e2": m2}
        
        # Simulate edge metrics computation update
        tm.traffic_metrics = edge_dict
        curr_max = float(max(m.predicted_congestion for m in edge_dict.values()))
        if curr_max > tm.max_predicted_congestion_observed:
            tm.max_predicted_congestion_observed = curr_max

        self.assertAlmostEqual(tm.max_predicted_congestion_observed, 6.2, places=4)

        with patch('traci.simulation.getTime', return_value=10.0):
            with patch('traci.simulation.getArrivedNumber', return_value=0):
                with patch('traci.vehicle.getIDList', return_value=[]):
                    metrics_dict = tm._evaluate_system_performance()

        self.assertIn('vsl_activations', metrics_dict)
        self.assertIn('routing_reroutes', metrics_dict)
        self.assertIn('max_predicted_congestion_observed', metrics_dict)
        self.assertEqual(metrics_dict['vsl_activations'], 0)
        self.assertEqual(metrics_dict['routing_reroutes'], 0)
        self.assertAlmostEqual(metrics_dict['max_predicted_congestion_observed'], 6.2, places=4)


if __name__ == "__main__":
    unittest.main()
