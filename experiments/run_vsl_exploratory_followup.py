"""
Exploratory VSL Signal-Aware Coordination Probe.
Evaluates 5 seeds of 'vsl_signal_aware' (Signals + VSL + Routing with green-phase speed bypass)
on grid_3_moderate_single_peak to test if a minimal signal-aware guard resolves VSL speed throttling.
"""

import sys
import os
import json
import subprocess
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
run_py = repo_root / "backend" / "run.py"
output_dir = repo_root / "experiments" / "results"
manifest_path = output_dir / "sweep_manifest.jsonl"

scenario = "grid_3_moderate_single_peak"
seeds = [1, 2, 3, 4, 5]

results = []

for seed in seeds:
    cmd = [
        sys.executable,
        str(run_py),
        "--mode", "batch",
        "--scenario", scenario,
        "--seed", str(seed),
        "--headless",
        "--steps", "500",
        "--signal-strategy", "pso",
        "--routing-strategy", "adaptive",
        "--enable-signals",
        "--enable-vsl",
        "--enable-routing",
        "--vsl-signal-aware",
        "--output-dir", str(output_dir)
    ]
    
    print(f"Running exploratory probe: seed={seed}...", flush=True)
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode == 0:
        lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
        for l in reversed(lines):
            if l.startswith("{") and l.endswith("}"):
                try:
                    summary = json.loads(l)
                    fm = summary.get("final_metrics", {})
                    results.append({
                        "seed": seed,
                        "avg_speed": fm.get("avg_speed", 0.0),
                        "total_travel_time": fm.get("total_travel_time", 0.0),
                        "total_vehicles": fm.get("total_vehicles", 0.0),
                        "avg_waiting_time": fm.get("avg_waiting_time", 0.0)
                    })
                    print(f"  Seed {seed} finished: Speed={fm.get('avg_speed', 0.0):.2f} m/s, TTT={fm.get('total_travel_time', 0.0):.0f}s", flush=True)
                    break
                except Exception:
                    pass

print("\nExploratory probe execution complete.")
