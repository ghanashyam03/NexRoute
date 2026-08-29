"""
Unit tests for _compute_edge_metrics density, flow rate, occupancy, and congestion index calculations.

Verifies:
  1. Hand-computed expected values for HCM density, flow rate, occupancy percentage, and congestion index.
  2. Vehicle state aggregation (PCU weighting, speed averaging, queue detection, stop counting).
"""

import sys
import unittest
from unittest.mock import MagicMock
from collections import defaultdict
from pathlib import Path
import numpy as np

# Add repository root to sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.traffic_manager import AdvancedTrafficManager, VehicleState, TrafficMetrics


class TestEdgeMetricsCalculation(unittest.TestCase):
    """Test suite for _compute_edge_metrics mathematical formulas."""

    def test_compute_edge_metrics_hand_computed(self):
        """
        Verify edge metrics calculations against a hand-constructed synthetic scenario.

        Hand Calculation:
          Edge Properties:
            length = 500.0 meters (0.5 km)
            lanes = 2 lanes
            network capacity = 72000.0 vehicles/hour

          Synthetic Vehicles on Edge 'edge_1':
            Vehicle 1: passenger car (PCU = 1.0), speed = 15.0 m/s, acceleration = 0.5 m/s^2
            Vehicle 2: bus (PCU = 2.0), speed = 0.5 m/s (queue < 1.0, stop < 0.1 False), acceleration = -0.2 m/s^2
            Vehicle 3: truck (PCU = 1.5), speed = 0.0 m/s (queue < 1.0 True, stop < 0.1 True), acceleration = 0.0 m/s^2

          Aggregated Raw Values:
            speeds = [15.0, 0.5, 0.0] -> avg_speed = 5.1667 m/s
            volumes (PCU sum) = 1.0 + 2.0 + 1.5 = 4.5 PCUs
            queues (speed < 1.0) = 2 (Bus & Truck)
            stops (speed < 0.1) = 1 (Truck)

          Calculated Formulas (traffic_manager.py lines 542-556):
            1. density = volume / (edge_length / 1000) / num_lanes
                       = 4.5 / (500 / 1000) / 2
                       = 4.5 / 0.5 / 2
                       = 4.5 / 1.0
                       = 4.5 vehicles/km/lane

            2. flow_rate = volume * 3600
                         = 4.5 * 3600
                         = 16200.0 vehicles/hour

            3. occupancy = min(100.0, (density / 130.0) * 100.0)
                         = min(100.0, (4.5 / 130.0) * 100.0)
                         = 3.4615%

            4. congestion_index = min(1.0, flow_rate / capacity)
                                = min(1.0, 16200.0 / 72000.0)
                                = 0.225
        """
        # Create uninitialized AdvancedTrafficManager instance
        tm = AdvancedTrafficManager.__new__(AdvancedTrafficManager)
        tm.traffic_metrics = defaultdict(TrafficMetrics)
        tm.edge_congestion_history = defaultdict(list)
        tm.PCU_VALUES = {"passenger": 1.0, "bus": 2.0, "truck": 1.5}
        tm.CONGESTION_HISTORY_SIZE = 10
        tm.max_predicted_congestion_observed = 0.0

        # Mock NetworkX graph capacity
        tm.network_graph = {
            "node_A": {
                "node_B": {"capacity": 72000.0}
            }
        }

        # Mock SUMO net structure
        mock_node_A = MagicMock()
        mock_node_A.getID.return_value = "node_A"
        mock_node_B = MagicMock()
        mock_node_B.getID.return_value = "node_B"

        mock_lane = MagicMock()
        mock_edge = MagicMock()
        mock_edge.getID.return_value = "edge_1"
        mock_edge.getLength.return_value = 500.0
        mock_edge.getLanes.return_value = [mock_lane, mock_lane]  # 2 lanes
        mock_edge.getFromNode.return_value = mock_node_A
        mock_edge.getToNode.return_value = mock_node_B
        mock_edge.getSpeed.return_value = 13.89
        mock_edge.getOutgoing.return_value = []

        tm.net = MagicMock()
        tm.net.getEdges.return_value = [mock_edge]
        tm.net.getEdge.return_value = mock_edge

        # Synthetic Vehicle States
        tm.vehicle_states = {
            "v1": VehicleState(
                id="v1", type="passenger", position=(100, 0), speed=15.0, route=["edge_1"],
                current_edge="edge_1", destination="edge_1", reroute_attempts=0, priority=1.0,
                last_reroute_time=0, waiting_time=0, lane_position=100.0, acceleration=0.5,
                last_speed=15.0, last_position=(100, 0)
            ),
            "v2": VehicleState(
                id="v2", type="bus", position=(200, 0), speed=0.5, route=["edge_1"],
                current_edge="edge_1", destination="edge_1", reroute_attempts=0, priority=1.5,
                last_reroute_time=0, waiting_time=10, lane_position=200.0, acceleration=-0.2,
                last_speed=0.5, last_position=(200, 0)
            ),
            "v3": VehicleState(
                id="v3", type="truck", position=(300, 0), speed=0.0, route=["edge_1"],
                current_edge="edge_1", destination="edge_1", reroute_attempts=0, priority=1.2,
                last_reroute_time=0, waiting_time=30, lane_position=300.0, acceleration=0.0,
                last_speed=0.0, last_position=(300, 0)
            ),
        }

        # Run _compute_edge_metrics
        computed_metrics = tm._compute_edge_metrics()

        self.assertIn("edge_1", computed_metrics)
        m = computed_metrics["edge_1"]

        # Assert Volume (PCU sum)
        self.assertAlmostEqual(m.volume, 4.5, places=4)

        # Assert Average Speed
        self.assertAlmostEqual(m.avg_speed, (15.0 + 0.5 + 0.0) / 3.0, places=4)

        # Assert Queues & Stops
        self.assertEqual(m.queue_length, 2)
        self.assertEqual(m.stop_count, 1)

        # Assert HCM Density
        self.assertAlmostEqual(m.density, 4.5, places=4)

        # Assert Flow Rate
        self.assertAlmostEqual(m.flow_rate, 16200.0, places=4)

        # Assert Occupancy Percentage
        expected_occ = (4.5 / 130.0) * 100.0
        self.assertAlmostEqual(m.occupancy, expected_occ, places=4)

        # Assert Congestion Index
        expected_ci = 16200.0 / 72000.0
        self.assertAlmostEqual(m.congestion_index, expected_ci, places=4)


if __name__ == "__main__":
    unittest.main()
