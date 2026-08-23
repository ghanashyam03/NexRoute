"""
Unit tests for Congestion Prediction Weight Search & Seed Validation.

Verifies:
  1. Property-based check: normalize_weights correctly enforces sum=1.0 and non-negativity across 100+ random draws.
  2. Running best score tracking in CongestionWeightOptimizer loop.
  3. CRITICAL: validate_seed_split raises ValueError when search and held-out seeds overlap.
"""

import sys
import unittest
import numpy as np
from pathlib import Path

# Add repository root to sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.congestion_weight_search import (
    DEFAULT_CONGESTION_WEIGHTS,
    normalize_weights,
    validate_seed_split,
    sample_random_weight_vector,
    CongestionWeightOptimizer
)


class TestCongestionWeightSearchCore(unittest.TestCase):
    """Test suite for weight normalization, optimizer state tracking, and seed split validation."""

    def test_property_based_normalization_100_draws(self):
        """Property-based check: verify normalize_weights enforces sum=1.0 and non-negativity across 100+ draws."""
        np.random.seed(42)
        for i in range(120):
            # Draw random raw vector with positive, zero, and negative values
            raw = np.random.uniform(-2.0, 5.0, size=7)
            normalized = normalize_weights(raw)

            # Assert length is 7
            self.assertEqual(len(normalized), 7)

            # Assert non-negativity
            for w in normalized:
                self.assertGreaterEqual(w, 0.0, f"Draw {i}: weight {w} is negative")

            # Assert sum equals 1.0 within float precision
            total_sum = sum(normalized)
            self.assertAlmostEqual(
                total_sum, 1.0, places=6,
                msg=f"Draw {i}: normalized sum {total_sum} does not equal 1.0"
            )

    def test_running_best_score_tracking(self):
        """Verify CongestionWeightOptimizer correctly tracks and updates running best weights/scores."""
        opt = CongestionWeightOptimizer(DEFAULT_CONGESTION_WEIGHTS)
        self.assertEqual(opt.best_score, float('inf'))

        w1 = [0.30, 0.20, 0.10, 0.10, 0.10, 0.10, 0.10]
        w2 = [0.10, 0.10, 0.10, 0.10, 0.10, 0.20, 0.30]

        # Register Candidate 1 (Score = 50.0) -> New Best
        is_improved1 = opt.register_candidate(w1, score=50.0)
        self.assertTrue(is_improved1)
        self.assertEqual(opt.best_score, 50.0)
        np.testing.assert_allclose(opt.best_weights, normalize_weights(w1), atol=1e-5)

        # Register Candidate 2 (Score = 60.0) -> Worse, No Update
        is_improved2 = opt.register_candidate(w2, score=60.0)
        self.assertFalse(is_improved2)
        self.assertEqual(opt.best_score, 50.0)
        np.testing.assert_allclose(opt.best_weights, normalize_weights(w1), atol=1e-5)

        # Register Candidate 3 (Score = 40.0) -> New Best
        is_improved3 = opt.register_candidate(w2, score=40.0)
        self.assertTrue(is_improved3)
        self.assertEqual(opt.best_score, 40.0)
        np.testing.assert_allclose(opt.best_weights, normalize_weights(w2), atol=1e-5)

    def test_seed_split_disjoint_validation_raises_error_on_overlap(self):
        """CRITICAL: Verify validate_seed_split raises ValueError when search and held-out seeds overlap."""
        # Case A: Valid disjoint seeds -> should pass without error
        search_valid = [1, 2, 3]
        heldout_valid = [4, 5, 6]
        try:
            validate_seed_split(search_valid, heldout_valid)
        except ValueError as e:
            self.fail(f"validate_seed_split raised unexpected ValueError on disjoint sets: {e}")

        # Case B: Overlapping seed (seed 3 in both sets) -> MUST raise ValueError
        search_overlap = [1, 2, 3]
        heldout_overlap = [3, 4, 5]
        with self.assertRaises(ValueError) as ctx:
            validate_seed_split(search_overlap, heldout_overlap)

        err_msg = str(ctx.exception)
        self.assertIn("CRITICAL ERROR", err_msg)
        self.assertIn("3", err_msg)


if __name__ == "__main__":
    unittest.main()
