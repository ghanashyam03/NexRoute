"""
Hyperparameter Search Orchestrator for Congestion Prediction Weight Vector.

Searches 7-dimensional weight space (sum=1.0) using random Dirichlet candidate sampling
evaluated strictly across --search-seeds. Held-out evaluation is performed ONCE at the end
on --heldout-seeds for both default hardcoded weights and best candidate weights found.

Guarantees:
  1. Strict disjoint check between --search-seeds and --heldout-seeds (fails loudly if overlap).
  2. Search decisions influenced exclusively by --search-seeds.
  3. Non-circular held-out evaluation on unseen traffic realization seeds.
"""

import sys
import os
import json
import argparse
import subprocess
import logging
from typing import List, Dict, Any, Tuple, Sequence, Optional
from pathlib import Path
import numpy as np

# Add repository root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.congestion_weight_search import (
    DEFAULT_CONGESTION_WEIGHTS,
    normalize_weights,
    validate_seed_split,
    sample_random_weight_vector,
    CongestionWeightOptimizer
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("experiments.search_congestion_weights")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Hyperparameter Search over Congestion Prediction Weights Vector"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="grid_3_light",
        help="Target scenario name for evaluation (default: 'grid_3_light')"
    )
    parser.add_argument(
        "--search-seeds",
        type=str,
        default="1,2,3",
        help="Comma-separated integer seeds for search objective evaluation (default: '1,2,3')"
    )
    parser.add_argument(
        "--heldout-seeds",
        type=str,
        default="4,5,6",
        help="Comma-separated integer seeds for held-out validation ONLY (default: '4,5,6')"
    )
    parser.add_argument(
        "--n-candidates",
        type=int,
        default=20,
        help="Number of random candidate weight vectors to sample during search budget (default: 20)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=500,
        help="Simulation duration steps per evaluation run (default: 500)"
    )
    parser.add_argument(
        "--target-metric",
        type=str,
        default="avg_waiting_time",
        help="Optimization target metric to minimize (default: 'avg_waiting_time')"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/results",
        help="Output directory path for search results (default: 'experiments/results')"
    )
    return parser.parse_args()


def parse_seed_list(seed_str: str) -> List[int]:
    """Parse comma-separated seed string into list of unique integers."""
    return [int(s.strip()) for s in seed_str.split(",") if s.strip()]


def evaluate_weights_on_seeds(
    weights: List[float],
    scenario: str,
    seeds: List[int],
    steps: int,
    target_metric: str,
    output_dir: Path
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Evaluate a candidate weight vector by running batch simulation across specified seeds.
    
    Returns:
        Tuple[float, List[Dict]]: (mean target metric score across seeds, list of seed-level metric dicts)
    """
    weights_str = ",".join(f"{w:.6f}" for w in weights)
    seed_results = []
    scores = []

    temp_run_dir = output_dir / "temp_runs"
    temp_run_dir.mkdir(parents=True, exist_ok=True)

    for seed in seeds:
        cmd = [
            sys.executable,
            "backend/run.py",
            "--mode", "batch",
            "--scenario", scenario,
            "--seed", str(seed),
            "--headless",
            "--steps", str(steps),
            "--output-dir", str(temp_run_dir),
            "--congestion-weights", weights_str
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root))
        if res.returncode != 0:
            logger.error(f"Batch run failed for seed {seed}:\n{res.stderr}")
            raise RuntimeError(f"Batch execution failed for seed {seed}: {res.stderr}")

        # Parse JSON summary output from stdout
        last_line = res.stdout.strip().split("\n")[-1]
        try:
            run_data = json.loads(last_line)
            metrics = run_data.get("final_metrics", {})
            score = float(metrics.get(target_metric, 1e6))
            scores.append(score)
            seed_results.append({
                "seed": seed,
                "metrics": metrics
            })
        except Exception as e:
            logger.error(f"Failed to parse output JSON from batch run: {e}")
            raise

    mean_score = float(np.mean(scores))
    return mean_score, seed_results


def main():
    args = parse_args()
    search_seeds = parse_seed_list(args.search_seeds)
    heldout_seeds = parse_seed_list(args.heldout_seeds)

    # CRITICAL: Fail loudly if any seed is in both search and held-out sets
    validate_seed_split(search_seeds, heldout_seeds)

    logger.info("======================================================================")
    logger.info("Starting Congestion Prediction Weight Vector Hyperparameter Search")
    logger.info("======================================================================")
    logger.info(f"Scenario: {args.scenario}")
    logger.info(f"Search Seeds ({len(search_seeds)}): {search_seeds}")
    logger.info(f"Held-Out Seeds ({len(heldout_seeds)}): {heldout_seeds}")
    logger.info(f"Candidate Budget: {args.n_candidates} random Dirichlet samples")
    logger.info(f"Simulation Steps per Run: {args.steps}")
    logger.info(f"Target Metric: {args.target_metric} (minimize)")
    logger.info("======================================================================")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    optimizer = CongestionWeightOptimizer(DEFAULT_CONGESTION_WEIGHTS)

    # Evaluate Candidate 0: Default hardcoded weights on search seeds
    logger.info("Evaluating Candidate 0 (Default Hardcoded Weights)...")
    default_search_score, default_search_details = evaluate_weights_on_seeds(
        weights=DEFAULT_CONGESTION_WEIGHTS,
        scenario=args.scenario,
        seeds=search_seeds,
        steps=args.steps,
        target_metric=args.target_metric,
        output_dir=output_dir
    )
    optimizer.register_candidate(DEFAULT_CONGESTION_WEIGHTS, default_search_score, {"candidate_id": 0, "type": "default"})
    logger.info(f"Candidate 0 (Default) Search Score: {default_search_score:.4f}")

    # Random Candidate Search Budget Loop
    for c_idx in range(1, args.n_candidates + 1):
        candidate_weights = sample_random_weight_vector(seed=42 + c_idx)
        logger.info(f"Evaluating Candidate {c_idx}/{args.n_candidates}: {np.round(candidate_weights, 3)}")

        score, details = evaluate_weights_on_seeds(
            weights=candidate_weights,
            scenario=args.scenario,
            seeds=search_seeds,
            steps=args.steps,
            target_metric=args.target_metric,
            output_dir=output_dir
        )

        is_new_best = optimizer.register_candidate(
            candidate_weights, score, {"candidate_id": c_idx, "type": "random_dirichlet"}
        )

        if is_new_best:
            logger.info(f"  --> NEW RUNNING BEST score found: {score:.4f} (improved from previous)")
        else:
            logger.info(f"  --> Score: {score:.4f} (Running Best: {optimizer.best_score:.4f})")

    best_weights = optimizer.best_weights
    logger.info("======================================================================")
    logger.info("Search Budget Complete.")
    logger.info(f"Best Search Score: {optimizer.best_score:.4f}")
    logger.info(f"Best Weight Vector: {np.round(best_weights, 4).tolist()}")
    logger.info("======================================================================")

    # FINAL HELD-OUT EVALUATION (Evaluated ONCE at the end on --heldout-seeds ONLY)
    logger.info("Executing Non-Circular Held-Out Seed Evaluation...")
    logger.info("  1. Evaluating Default Hardcoded Weights on Held-Out Seeds...")
    default_heldout_score, default_heldout_details = evaluate_weights_on_seeds(
        weights=DEFAULT_CONGESTION_WEIGHTS,
        scenario=args.scenario,
        seeds=heldout_seeds,
        steps=args.steps,
        target_metric=args.target_metric,
        output_dir=output_dir
    )

    logger.info("  2. Evaluating Best Found Weights on Held-Out Seeds...")
    best_heldout_score, best_heldout_details = evaluate_weights_on_seeds(
        weights=best_weights,
        scenario=args.scenario,
        seeds=heldout_seeds,
        steps=args.steps,
        target_metric=args.target_metric,
        output_dir=output_dir
    )

    # Save complete search log and held-out evaluation report
    results_payload = {
        "scenario": args.scenario,
        "search_seeds": search_seeds,
        "heldout_seeds": heldout_seeds,
        "target_metric": args.target_metric,
        "steps": args.steps,
        "default_weights": DEFAULT_CONGESTION_WEIGHTS,
        "best_weights": best_weights,
        "search_history": optimizer.history,
        "heldout_evaluation": {
            "default_heldout_score": default_heldout_score,
            "default_heldout_runs": default_heldout_details,
            "best_heldout_score": best_heldout_score,
            "best_heldout_runs": best_heldout_details
        }
    }

    output_json = output_dir / "weight_search_results.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    logger.info(f"Saved complete search log to: '{output_json}'")


if __name__ == "__main__":
    main()
