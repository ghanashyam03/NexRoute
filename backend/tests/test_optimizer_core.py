"""
Unit tests for core Particle Swarm Optimization (PSO) logic in backend/app/optimizer.py.

Verifies:
  1. Convergence to global minimum on known analytical benchmark function (Sphere function).
  2. Strict enforcement of particle search space boundary constraints across all iterations.
  3. Deterministic velocity and position math against hand-computed single-step arithmetic.
"""

import sys
import unittest
from unittest.mock import patch
import numpy as np
from pathlib import Path

# Add repository root to sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.optimizer import Particle, ParticleSwarmOptimizer


class TestParticleCoreMath(unittest.TestCase):
    """Test single-step velocity and position updates with hand-computed arithmetic."""

    def test_single_step_update_hand_computed(self):
        """
        Verify single-step velocity and position updates against hand-computed values.
        
        Hand Calculation:
          Initial State:
            position = [2.0, -1.0]
            velocity = [0.5, -0.2]
            best_position = [1.0, 0.0]
            global_best_position = [0.0, 0.0]
            w = 0.8, c1 = 1.5, c2 = 1.5
            patched r1 = 0.5, r2 = 0.5

          Step 1: Cognitive Component
            cognitive = c1 * r1 * (best_position - position)
                      = 1.5 * 0.5 * ([1.0, 0.0] - [2.0, -1.0])
                      = 0.75 * [-1.0, 1.0]
                      = [-0.75, 0.75]

          Step 2: Social Component
            social = c2 * r2 * (global_best_position - position)
                   = 1.5 * 0.5 * ([0.0, 0.0] - [2.0, -1.0])
                   = 0.75 * [-2.0, 1.0]
                   = [-1.50, 0.75]

          Step 3: New Velocity
            new_velocity = w * velocity + cognitive + social
                         = 0.8 * [0.5, -0.2] + [-0.75, 0.75] + [-1.50, 0.75]
                         = [0.40, -0.16] + [-2.25, 1.50]
                         = [-1.85, 1.34]

          Step 4: New Position
            bounds = [(-10.0, 10.0), (-10.0, 10.0)] (no clamping triggered)
            new_position = position + new_velocity
                         = [2.0, -1.0] + [-1.85, 1.34]
                         = [0.15, 0.34]
        """
        particle = Particle(
            position=np.array([2.0, -1.0]),
            velocity=np.array([0.5, -0.2]),
            best_position=np.array([1.0, 0.0]),
            best_score=5.0,
            current_score=5.0
        )
        global_best_pos = np.array([0.0, 0.0])
        bounds = [(-10.0, 10.0), (-10.0, 10.0)]

        # Patch random.random to return constant 0.5 for r1 and r2
        with patch("random.random", return_value=0.5):
            particle.update_velocity(global_best_pos, w=0.8, c1=1.5, c2=1.5)
            particle.update_position(bounds)

        expected_velocity = np.array([-1.85, 1.34])
        expected_position = np.array([0.15, 0.34])

        np.testing.assert_allclose(particle.velocity, expected_velocity, atol=1e-5)
        np.testing.assert_allclose(particle.position, expected_position, atol=1e-5)


class TestParticleSwarmOptimizerConvergence(unittest.TestCase):
    """Test convergence and bounds enforcement on analytic benchmark functions."""

    def test_sphere_function_convergence(self):
        """
        Verify PSO converges close to the known global minimum (0.0 at origin)
        for the 3D Sphere benchmark function: f(x, y, z) = x^2 + y^2 + z^2.
        """
        def sphere_func(x):
            return np.sum(x**2)

        bounds = [(-5.0, 5.0), (-5.0, 5.0), (-5.0, 5.0)]
        pso = ParticleSwarmOptimizer(
            num_particles=30,
            num_dimensions=3,
            bounds=bounds,
            objective_function=sphere_func,
            w=0.7,
            c1=1.5,
            c2=1.5,
            max_iterations=50
        )

        best_pos, best_score = pso.optimize(iterations=50)

        # Global minimum of sphere function is 0.0
        self.assertLess(best_score, 0.05, f"PSO failed to converge to near-zero minimum, got score {best_score}")
        np.testing.assert_allclose(best_pos, np.zeros(3), atol=0.25)

    def test_bounds_enforcement_during_optimization(self):
        """
        Verify particle positions NEVER violate configured bounds at any iteration during optimize().
        Assessed by auditing all particles after every single optimization step.
        """
        def dummy_obj(x):
            return np.sum(x**2)

        bounds = [(-2.0, 2.0), (-3.0, 3.0)]
        pso = ParticleSwarmOptimizer(
            num_particles=20,
            num_dimensions=2,
            bounds=bounds,
            objective_function=dummy_obj,
            w=1.5,  # High inertia weight to encourage boundary exploration
            c1=2.5,
            c2=2.5,
            max_iterations=30
        )

        for step in range(30):
            pso.optimize_step()
            for idx, p in enumerate(pso.particles):
                for dim, (low, high) in enumerate(bounds):
                    val = p.position[dim]
                    self.assertGreaterEqual(
                        val, low,
                        f"Step {step}, particle {idx}, dim {dim} value {val} below lower bound {low}"
                    )
                    self.assertLessEqual(
                        val, high,
                        f"Step {step}, particle {idx}, dim {dim} value {val} above upper bound {high}"
                    )


if __name__ == "__main__":
    unittest.main()
