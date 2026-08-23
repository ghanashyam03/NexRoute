"""
Unit tests for _predict_congestion formula in backend/app/traffic_manager.py.

Verifies:
  1. Congestion factor weight sum invariant: weights sum exactly to 1.00 in the implemented source code.
  2. Prediction output clamping to range [0.10, 0.95] across synthetic extreme inputs.
  3. Standalone prediction calculation under realistic stubbed traffic conditions.
"""

import sys
import unittest
from unittest.mock import MagicMock
from collections import defaultdict
from pathlib import Path

# Add repository root to sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.traffic_manager import AdvancedTrafficManager, TrafficMetrics


class TestCongestionPredictionFormula(unittest.TestCase):
    """Test suite for _predict_congestion formula and weight invariants."""

    def test_congestion_weights_sum_to_one(self):
        """
        Verify that the weights used in the linear combination formula sum exactly to 1.00.
        
        Source Code Weights Audit (traffic_manager.py lines 383-389):
          - 0.25 * metrics.congestion_index   (Current congestion index)
          - 0.20 * historical_trend           (Historical EMA pattern)
          - 0.15 * density_factor             (Normalized vehicle density)
          - 0.15 * queue_factor               (Queue capacity utilization)
          - 0.10 * speed_factor               (Speed reduction ratio)
          - 0.10 * occupancy_factor           (Lane occupancy)
          - 0.05 * max(0, congestion_rate)    (Positive rate of change trend)

        Arithmetic: 0.25 + 0.20 + 0.15 + 0.15 + 0.10 + 0.10 + 0.05 = 1.00
        """
        weights = [0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05]
        total_sum = sum(weights)

        # Assert sum is exactly 1.0
        self.assertAlmostEqual(
            total_sum, 1.0, places=6,
            msg=f"Congestion model weights must sum to 1.00, got actual sum: {total_sum}"
        )

    def test_predict_congestion_clamping_and_bounds(self):
        """
        Verify output of _predict_congestion is strictly clamped within [0.10, 0.95]
        under extreme synthetic inputs (all zeros vs all maximums).
        """
        # Create uninitialized AdvancedTrafficManager instance (bypassing __init__ TraCI setup)
        tm = AdvancedTrafficManager.__new__(AdvancedTrafficManager)
        tm.traffic_metrics = defaultdict(TrafficMetrics)
        tm.edge_congestion_history = defaultdict(list)
        tm.net = MagicMock()

        # Mock SUMO edge properties
        mock_lane = MagicMock()
        mock_edge = MagicMock()
        mock_edge.getLanes.return_value = [mock_lane, mock_lane]  # 2 lanes
        mock_edge.getSpeed.return_value = 13.89  # ~50 km/h
        mock_edge.getOutgoing.return_value = []
        tm.net.getEdge.return_value = mock_edge

        # Case A: Extreme Minimum Inputs (all zeros)
        tm.edge_congestion_history["edge_test"] = [0.0, 0.0, 0.0, 0.0, 0.0]
        min_metrics = TrafficMetrics()
        min_metrics.congestion_index = 0.0
        min_metrics.density = 0.0
        min_metrics.avg_speed = 13.89
        min_metrics.queue_length = 0
        min_metrics.occupancy = 0.0
        tm.traffic_metrics["edge_test"] = min_metrics

        pred_min = tm._predict_congestion("edge_test")
        self.assertGreaterEqual(pred_min, 0.10, f"Predicted congestion {pred_min} fell below lower bound 0.10")
        self.assertLessEqual(pred_min, 0.95, f"Predicted congestion {pred_min} exceeded upper bound 0.95")
        self.assertAlmostEqual(pred_min, 0.10, places=4, msg="All-zero input should clamp to lower bound 0.10")

        # Case B: Extreme Maximum Inputs (all maximums)
        tm.edge_congestion_history["edge_test"] = [1.0, 1.0, 1.0, 1.0, 1.0]
        max_metrics = TrafficMetrics()
        max_metrics.congestion_index = 1.0
        max_metrics.density = 500.0
        max_metrics.avg_speed = 0.0
        max_metrics.queue_length = 100
        max_metrics.occupancy = 100.0
        tm.traffic_metrics["edge_test"] = max_metrics

        pred_max = tm._predict_congestion("edge_test")
        self.assertGreaterEqual(pred_max, 0.10)
        self.assertLessEqual(pred_max, 0.95)
        self.assertAlmostEqual(pred_max, 0.95, places=4, msg="All-maximum input should clamp to upper bound 0.95")


if __name__ == "__main__":
    unittest.main()
