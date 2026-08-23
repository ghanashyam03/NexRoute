"""
Diagnostic Run Orchestrator for Hypothesis Gating (A) vs Wiring Bug (B) Verification.

Executes batch runs for:
  1. grid_3_light across seeds 1..5 for baseline, vsl_only, routing_only, and combined conditions.
  2. grid_5_moderate across seeds 1..3 for baseline, vsl_only, routing_only, and combined conditions.

Records per-run diagnostic metrics:
  - vsl_activations
  - routing_reroutes
  - max_predicted_congestion_observed
  - avg_waiting_time, avg_speed, total_travel_time, etc.
"""

import sys
import os
import json
import argparse
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("experiments.run_diagnostics")

# 5 Conditions
CONDITIONS = {
    "baseline": ["--signal-strategy", "webster", "--routing-strategy", "static", "--no-enable-signals", "--no-enable-vsl", "--no-enable-routing"],
    "signal_only": ["--signal-strategy", "pso", "--routing-strategy", "static", "--enable-signals", "--no-enable-vsl", "--no-enable-routing"],
    "vsl_only": ["--signal-strategy", "webster", "--routing-strategy", "static", "--no-enable-signals", "--enable-vsl", "--no-enable-routing"],
    "routing_only": ["--signal-strategy", "webster", "--routing-strategy", "adaptive", "--no-enable-signals", "--no-enable-vsl", "--enable-routing"],
    "combined": ["--signal-strategy", "pso", "--routing-strategy", "adaptive", "--enable-signals", "--enable-vsl", "--enable-routing"],
}


def run_single_diagnostic(scenario: str, seed: int, condition: str, steps: int, output_dir: Path) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        "backend/run.py",
        "--mode", "batch",
        "--scenario", scenario,
        "--seed", str(seed),
        "--headless",
        "--steps", str(steps),
        "--output-dir", str(output_dir)
    ] + CONDITIONS[condition]

    logger.info(f"Running diagnostic: {scenario} | seed={seed} | condition={condition}")
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root))
    if res.returncode != 0:
        logger.error(f"Execution failed for {scenario} seed={seed} condition={condition}:\n{res.stderr}")
        raise RuntimeError(f"Diagnostic run failed: {res.stderr}")

    last_line = res.stdout.strip().split("\n")[-1]
    try:
        run_data = json.loads(last_line)
        metrics = run_data.get("final_metrics", {})
        return {
            "scenario": scenario,
            "seed": seed,
            "condition": condition,
            "vsl_activations": metrics.get("vsl_activations", 0),
            "routing_reroutes": metrics.get("routing_reroutes", 0),
            "max_predicted_congestion_observed": metrics.get("max_predicted_congestion_observed", 0.0),
            "avg_waiting_time": metrics.get("avg_waiting_time", 0.0),
            "avg_speed": metrics.get("avg_speed", 0.0),
            "total_travel_time": metrics.get("total_travel_time", 0.0),
            "system_congestion": metrics.get("system_congestion", 0.0),
            "predicted_congestion": metrics.get("predicted_congestion", 0.0)
        }
    except Exception as e:
        logger.error(f"Failed to parse JSON output: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Run diagnostic comparison")
    parser.add_argument("--steps", type=int, default=100, help="Steps per run (default: 100)")
    parser.add_argument("--output-dir", type=str, default="experiments/results/diagnostics", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    target_conditions = ["baseline", "vsl_only", "routing_only", "combined"]

    # 1. Light scenario grid_3_light (seeds 1..5)
    light_seeds = [1, 2, 3, 4, 5]
    for seed in light_seeds:
        for cond in target_conditions:
            rec = run_single_diagnostic("grid_3_light", seed, cond, args.steps, out_dir)
            results.append(rec)

    # 2. Heavy scenario grid_5_moderate (seeds 1..3)
    heavy_seeds = [1, 2, 3]
    for seed in heavy_seeds:
        for cond in target_conditions:
            rec = run_single_diagnostic("grid_5_moderate", seed, cond, args.steps, out_dir)
            results.append(rec)

    # Save summary JSON
    diag_summary_file = out_dir / "diagnostic_results.json"
    with open(diag_summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Diagnostics complete. Saved raw results to: '{diag_summary_file}'")


if __name__ == "__main__":
    main()
