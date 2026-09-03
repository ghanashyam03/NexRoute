"""
VSL Harmonization Real Sweeper for NexRoute Paper.

Executes genuine stochastic simulation runs for VSL min speed floors 5.0, 8.0, 10.0 m/s
on grid_3_moderate_single_peak to generate real, non-placeholder empirical statistics.
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
MANIFEST = OUTPUT_DIR / "vsl_real_floor_manifest.jsonl"


def run_sweep():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    
    for floor in [5.0, 8.0, 10.0]:
        for seed in range(1, 11):
            logger.info(f"Running VSL floor={floor} m/s seed={seed}/10...")
            cmd = [
                sys.executable, str(RUN_PY),
                "--mode", "batch", "--scenario", "grid_3_moderate_single_peak", "--seed", str(seed),
                "--headless", "--steps", "1500",
                "--signal-strategy", "pso", "--routing-strategy", "adaptive",
                "--enable-signals", "--enable-vsl", "--no-enable-routing",
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
                            row = {
                                "vsl_min_speed": floor,
                                "seed": seed,
                                "avg_speed": fm.get("avg_speed", 0.0),
                                "total_travel_time": fm.get("total_travel_time", 0.0),
                                "avg_waiting_time": fm.get("avg_waiting_time", 0.0),
                                "total_stops": fm.get("total_stops", 0),
                                "vsl_activations": fm.get("vsl_activations", 0)
                            }
                            results.append(row)
                            with open(MANIFEST, "a", encoding="utf-8") as f:
                                f.write(json.dumps(row) + "\n")
                            break
                        except Exception as e:
                            logger.error(f"JSON parse error floor {floor} seed {seed}: {e}")

    df = pd.DataFrame(results)
    if not df.empty:
        logger.info("=== REAL VSL FLOOR SENSITIVITY RESULTS ===")
        print(df.groupby("vsl_min_speed")[["avg_speed", "total_travel_time", "avg_waiting_time"]].agg(["mean", "std"]))


if __name__ == "__main__":
    run_sweep()
