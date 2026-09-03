"""
High-Speed Interleaved Unified Parallel Runner for NexRoute Sweeps (VSL + Threshold Sensitivity).

Interleaves VSL and Threshold tasks into a single unified queue across 6 parallel worker threads.
Auto-resumes from all 167 completed manifest runs.
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

VSL_MANIFEST = OUTPUT_DIR / "vsl_harmonization_manifest.jsonl"
TH_MANIFEST = OUTPUT_DIR / "threshold_sensitivity_manifest.jsonl"

SCENARIOS = [
    "grid_3_light",
    "grid_3_moderate_single_peak",
    "grid_3_moderate_two_peak",
    "grid_5_moderate",
    "real_sf_downtown"
]
FLOORS = [5.0, 8.0, 10.0]
THRESHOLDS = [0.40, 0.50, 0.60, 0.65, 0.70, 0.80]
SEEDS = list(range(1, 11))


def load_completed_vsl() -> set:
    completed = set()
    if VSL_MANIFEST.exists():
        with open(VSL_MANIFEST, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("{"):
                    try:
                        d = json.loads(line)
                        completed.add((d["scenario"], float(d["vsl_min_speed"]), int(d["seed"])))
                    except Exception:
                        pass
    return completed


def load_completed_th() -> set:
    completed = set()
    if TH_MANIFEST.exists():
        with open(TH_MANIFEST, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("{"):
                    try:
                        d = json.loads(line)
                        completed.add((d["scenario"], float(d["routing_threshold"]), int(d["seed"])))
                    except Exception:
                        pass
    return completed


def run_cell(task_info):
    task_type = task_info[0]
    if task_type == "vsl":
        _, sc, floor, seed = task_info
        steps = "1000" if sc == "grid_3_light" else "1500"
        cmd = [
            sys.executable, str(RUN_PY),
            "--mode", "batch", "--scenario", sc, "--seed", str(seed),
            "--headless", "--steps", steps,
            "--signal-strategy", "pso", "--routing-strategy", "adaptive",
            "--enable-signals", "--enable-vsl", "--enable-routing",
            "--vsl-min-speed", str(floor), "--output-dir", str(OUTPUT_DIR)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            for l in reversed(lines):
                if l.startswith("{") and l.endswith("}"):
                    try:
                        summary = json.loads(l)
                        fm = summary.get("final_metrics", {})
                        return {
                            "type": "vsl",
                            "scenario": sc, "vsl_min_speed": floor, "seed": seed,
                            "avg_speed": fm.get("avg_speed", 0.0),
                            "total_travel_time": fm.get("total_travel_time", 0.0),
                            "avg_waiting_time": fm.get("avg_waiting_time", 0.0),
                            "vsl_activations": fm.get("vsl_activations", 0),
                            "routing_reroutes": fm.get("routing_reroutes", 0)
                        }
                    except Exception:
                        pass
    elif task_type == "th":
        _, sc, th, seed = task_info
        steps = "1000" if sc == "grid_3_light" else "1500"
        cmd = [
            sys.executable, str(RUN_PY),
            "--mode", "batch", "--scenario", sc, "--seed", str(seed),
            "--headless", "--steps", steps,
            "--signal-strategy", "pso", "--routing-strategy", "adaptive",
            "--enable-signals", "--no-enable-vsl", "--enable-routing",
            "--routing-threshold", str(th), "--output-dir", str(OUTPUT_DIR)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            for l in reversed(lines):
                if l.startswith("{") and l.endswith("}"):
                    try:
                        summary = json.loads(l)
                        fm = summary.get("final_metrics", {})
                        return {
                            "type": "th",
                            "scenario": sc, "routing_threshold": th, "seed": seed,
                            "avg_speed": fm.get("avg_speed", 0.0),
                            "total_travel_time": fm.get("total_travel_time", 0.0),
                            "avg_waiting_time": fm.get("avg_waiting_time", 0.0),
                            "routing_reroutes": fm.get("routing_reroutes", 0)
                        }
                    except Exception:
                        pass
    return None


def main(workers: int = 6):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    comp_vsl = load_completed_vsl()
    comp_th = load_completed_th()
    
    logger.info(f"Loaded existing completions: VSL={len(comp_vsl)} runs, TH={len(comp_th)} runs. Total={len(comp_vsl)+len(comp_th)}.")

    vsl_tasks = [("vsl", sc, fl, sd) for sc in SCENARIOS for fl in FLOORS for sd in SEEDS if (sc, float(fl), int(sd)) not in comp_vsl]
    th_tasks = [("th", sc, th, sd) for sc in SCENARIOS for th in THRESHOLDS for sd in SEEDS if (sc, float(th), int(sd)) not in comp_th]

    all_tasks = []
    # Interleave VSL and Threshold tasks for maximum parallel speedup
    max_len = max(len(vsl_tasks), len(th_tasks))
    for i in range(max_len):
        if i < len(vsl_tasks):
            all_tasks.append(vsl_tasks[i])
        if i < len(th_tasks):
            all_tasks.append(th_tasks[i])

    logger.info(f"Interleaved queue: {len(all_tasks)} total remaining tasks across {workers} parallel workers...")

    if not all_tasks:
        logger.info("ALL SWEEPS ARE 100% COMPLETE!")
        return

    completed_count = 0
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_cell, t): t for t in all_tasks}
        for f in as_completed(futures):
            res = f.result()
            completed_count += 1
            if res:
                ttype = res.pop("type", None)
                if ttype == "vsl":
                    with open(VSL_MANIFEST, "a", encoding="utf-8") as out:
                        out.write(json.dumps(res) + "\n")
                    logger.info(f"[{completed_count}/{len(all_tasks)}] [VSL] {res['scenario']} floor={res['vsl_min_speed']} seed={res['seed']}: Speed={res['avg_speed']:.2f} m/s")
                elif ttype == "th":
                    with open(TH_MANIFEST, "a", encoding="utf-8") as out:
                        out.write(json.dumps(res) + "\n")
                    logger.info(f"[{completed_count}/{len(all_tasks)}] [TH] {res['scenario']} th={res['routing_threshold']} seed={res['seed']}: Speed={res['avg_speed']:.2f} m/s")

    logger.info("ALL UNIFIED PARALLEL SWEEPS COMPLETE!")


if __name__ == "__main__":
    main(workers=6)
