"""
Parallel Threshold Sensitivity Sweep (C_pred in [0.40, 0.50, 0.60, 0.65, 0.70, 0.80] with N=10 Seeds across 5 Topologies).

Evaluates threshold sensitivity curve in parallel across:
  - grid_3_light (N=10)
  - grid_3_moderate_single_peak (N=10)
  - grid_3_moderate_two_peak (N=10)
  - grid_5_moderate (N=10)
  - real_sf_downtown (N=10)
"""

import sys
import os
import json
import subprocess
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_PY = REPO_ROOT / "backend" / "run.py"
OUTPUT_DIR = REPO_ROOT / "experiments" / "results"
MANIFEST_PATH = OUTPUT_DIR / "threshold_sensitivity_manifest.jsonl"

SCENARIOS = [
    "grid_3_light",
    "grid_3_moderate_single_peak",
    "grid_3_moderate_two_peak",
    "grid_5_moderate",
    "real_sf_downtown"
]
THRESHOLDS = [0.40, 0.50, 0.60, 0.65, 0.70, 0.80]
SEEDS = list(range(1, 11))


def load_completed() -> set:
    completed = set()
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and line.startswith("{"):
                    try:
                        d = json.loads(line)
                        completed.add((d["scenario"], float(d["routing_threshold"]), int(d["seed"])))
                    except Exception:
                        pass
    return completed


def run_single_cell(args):
    sc, th, seed = args
    steps = "3600" if sc != "grid_3_light" else "1000"
    cmd = [
        sys.executable,
        str(RUN_PY),
        "--mode", "batch",
        "--scenario", sc,
        "--seed", str(seed),
        "--headless",
        "--steps", steps,
        "--signal-strategy", "pso",
        "--routing-strategy", "adaptive",
        "--enable-signals",
        "--no-enable-vsl",
        "--enable-routing",
        "--routing-threshold", str(th),
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
                    rec = {
                        "scenario": sc,
                        "routing_threshold": th,
                        "seed": seed,
                        "avg_speed": fm.get("avg_speed", 0.0),
                        "total_travel_time": fm.get("total_travel_time", 0.0),
                        "avg_waiting_time": fm.get("avg_waiting_time", 0.0),
                        "routing_reroutes": fm.get("routing_reroutes", 0)
                    }
                    return rec
                except Exception:
                    pass
    return None


def run_sweep(workers: int = 4):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    completed = load_completed()
    logger.info(f"Loaded {len(completed)} existing completed runs from manifest.")

    tasks = []
    for sc in SCENARIOS:
        for th in THRESHOLDS:
            for seed in SEEDS:
                if (sc, float(th), int(seed)) not in completed:
                    tasks.append((sc, th, seed))

    total_tasks = len(tasks)
    logger.info(f"Starting Parallel Threshold Sensitivity Sweep: {total_tasks} remaining tasks across {workers} parallel workers...")

    if not tasks:
        logger.info("All Threshold Sensitivity runs are already complete!")
        return

    completed_count = 0
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_cell, t): t for t in tasks}
        for future in as_completed(futures):
            res = future.result()
            completed_count += 1
            if res:
                with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(res) + "\n")
                logger.info(f"[{completed_count}/{total_tasks}] Finished cell {res['scenario']} threshold={res['routing_threshold']} seed={res['seed']}: Speed={res['avg_speed']:.2f} m/s")

    logger.info("Threshold Sensitivity Sweep Complete!")


if __name__ == "__main__":
    run_sweep(workers=4)
