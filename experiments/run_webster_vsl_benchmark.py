"""
Webster + VSL Benchmark Evaluator for NexRoute Paper.

Executes 10 seeds of Webster Fixed-Time Signals + VSL (webster_and_vsl)
on grid_3_moderate_single_peak to complete the benchmark matrix.
"""

import sys
import json
import subprocess
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_PY = REPO_ROOT / "backend" / "run.py"
OUTPUT_DIR = REPO_ROOT / "experiments" / "results"
MANIFEST = OUTPUT_DIR / "webster_vsl_manifest.jsonl"


def run_webster_vsl():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    
    for seed in range(1, 11):
        logger.info(f"Running webster_and_vsl for seed {seed}/10...")
        cmd = [
            sys.executable, str(RUN_PY),
            "--mode", "batch", "--scenario", "grid_3_moderate_single_peak", "--seed", str(seed),
            "--headless", "--steps", "1500",
            "--signal-strategy", "webster", "--routing-strategy", "adaptive",
            "--enable-signals", "--enable-vsl", "--no-enable-routing",
            "--output-dir", str(OUTPUT_DIR)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            for l in reversed(lines):
                if l.startswith("{") and l.endswith("}"):
                    try:
                        summary = json.loads(l)
                        fm = summary.get("final_metrics", {})
                        row = {
                            "condition": "webster_and_vsl",
                            "scenario": "grid_3_moderate_single_peak",
                            "seed": seed,
                            "avg_speed": fm.get("avg_speed", 0.0),
                            "total_travel_time": fm.get("total_travel_time", 0.0),
                            "avg_waiting_time": fm.get("avg_waiting_time", 0.0),
                            "total_stops": fm.get("total_stops", 0),
                            "vsl_activations": fm.get("vsl_activations", 0),
                            "routing_reroutes": fm.get("routing_reroutes", 0)
                        }
                        results.append(row)
                        with open(MANIFEST, "a", encoding="utf-8") as f:
                            f.write(json.dumps(row) + "\n")
                        break
                    except Exception as e:
                        logger.error(f"JSON error seed {seed}: {e}")

    df = pd.DataFrame(results)
    if not df.empty:
        logger.info("=== WEBSTER + VSL EMPIRICAL RESULTS (N=10) ===")
        logger.info(f"Avg Speed: {df['avg_speed'].mean():.2f} +/- {df['avg_speed'].std():.2f} m/s")
        logger.info(f"Travel Time: {df['total_travel_time'].mean():.0f} +/- {df['total_travel_time'].std():.0f} s")
        logger.info(f"Waiting Time: {df['avg_waiting_time'].mean():.1f} +/- {df['avg_waiting_time'].std():.1f} s")


if __name__ == "__main__":
    run_webster_vsl()
