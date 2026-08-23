"""
Congestion Prediction Weight Vector Optimization & Normalization Module.

Provides:
  1. Default 7-element weight vector constants.
  2. Weight vector normalization helper functions enforcing non-negativity and sum-to-1.0.
  3. Seed split validation enforcing strict non-overlapping disjoint set constraints.
  4. Search optimizer engine tracking running best candidates over objective evaluations.
"""

import logging
from typing import List, Sequence, Tuple, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("app.congestion_weight_search")

# Default 7-element hand-picked congestion prediction weights
DEFAULT_CONGESTION_WEIGHTS: List[float] = [0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05]


def normalize_weights(weights: Sequence[float]) -> List[float]:
    """
    Normalize a 7-element weight vector so all elements are non-negative and sum to 1.0.
    
    If all input weights are zero or negative, returns the default weight vector.
    """
    arr = np.array(weights, dtype=float)
    arr = np.maximum(0.0, arr)
    total = np.sum(arr)
    if total <= 1e-12:
        return list(DEFAULT_CONGESTION_WEIGHTS)
    normalized = arr / total
    return normalized.tolist()


def validate_seed_split(search_seeds: Sequence[int], heldout_seeds: Sequence[int]) -> None:
    """
    Validate that search seeds and held-out seeds are strictly disjoint sets.
    
    Raises:
        ValueError: If any seed appears in both search_seeds and heldout_seeds.
    """
    search_set = set(search_seeds)
    heldout_set = set(heldout_seeds)
    overlap = search_set.intersection(heldout_set)
    if overlap:
        sorted_overlap = sorted(list(overlap))
        raise ValueError(
            f"CRITICAL ERROR: Search seeds and held-out seeds must be strictly disjoint! "
            f"Overlapping seed(s) found in both sets: {sorted_overlap}. "
            f"Search seeds: {sorted(list(search_set))}, Held-out seeds: {sorted(list(heldout_set))}."
        )


def sample_random_weight_vector(seed: Optional[int] = None) -> List[float]:
    """Sample a random 7-element weight vector uniformly from Dirichlet distribution (sum=1.0)."""
    if seed is not None:
        np.random.seed(seed)
    # Uniform Dirichlet sampling over 7 simplex dimensions
    weights = np.random.dirichlet(np.ones(7))
    return weights.tolist()


class CongestionWeightOptimizer:
    """
    Tracks running best weight candidate, history logs, and evaluation metrics during hyperparameter search.
    """

    def __init__(self, initial_weights: Optional[Sequence[float]] = None):
        if initial_weights is None:
            self.best_weights = list(DEFAULT_CONGESTION_WEIGHTS)
        else:
            self.best_weights = normalize_weights(initial_weights)

        self.best_score: float = float('inf')
        self.history: List[Dict[str, Any]] = []

    def register_candidate(self, weights: Sequence[float], score: float, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Record a candidate evaluation result. Updates running best if score improves.
        
        Returns:
            bool: True if the candidate set a new running best score, False otherwise.
        """
        norm_weights = normalize_weights(weights)
        is_improved = score < self.best_score
        if is_improved:
            self.best_score = score
            self.best_weights = norm_weights

        record = {
            "weights": norm_weights,
            "score": score,
            "is_best": is_improved,
            "metadata": metadata or {}
        }
        self.history.append(record)
        return is_improved
