"""
NexRoute Specific Sweep Script for Dual Component (signal_and_routing).
Runs signal_and_routing across grid_3_moderate_single_peak and grid_3_moderate_two_peak for seeds 1-10.
"""

import sys
import os
import json
import subprocess
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
run_py = repo_root / "backend" / "run.py"
manifest_path = repo_root / "experiments" / "results" / "sweep_manifest.jsonl"

scenarios = ["grid_3_moderate_single_peak", "grid_3_moderate_two_peak"]
seeds = list(range(1, 11))

completed = set()
if manifest_path.exists():
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if not r.get("error"):
                    completed.add((r["scenario"], r["seed"], r["condition"]))

for sc in scenarios:
    for seed in seeds:
        if (sc, seed, "signal_and_routing") in completed:
            print(f"Skipping already completed cell: scenario='{sc}', seed={seed}, condition='signal_and_routing'", flush=True)
            continue
        print(f"\n==================================================", flush=True)
        print(f"Running scenario='{sc}', seed={seed}, condition='signal_and_routing'", flush=True)
        print(f"==================================================", flush=True)
        
        cmd = [
            sys.executable,
            str(run_py),
            "--mode", "batch",
            "--scenario", sc,
            "--seed", str(seed),
            "--headless",
            "--steps", "500",
            "--signal-strategy", "pso",
            "--routing-strategy", "adaptive",
            "--enable-signals",
            "--no-enable-vsl",
            "--enable-routing",
            "--output-dir", str(repo_root / "experiments" / "results")
        ]
        
        start_time = os.times().elapsed
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            summary_data = json.loads(res.stdout.strip())
            exit_code = 0
            err_msg = None
        except Exception as e:
            print(f"Error running cell: {e}")
            summary_data = None
            exit_code = 1
            err_msg = str(e)
            
        dur = os.times().elapsed - start_time
        
        manifest_record = {
            "scenario": sc,
            "seed": seed,
            "condition": "signal_and_routing",
            "exit_code": exit_code,
            "duration_seconds": round(dur, 2),
            "cmd": cmd,
            "summary": summary_data,
            "error": err_msg
        }
        
        with open(manifest_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(manifest_record) + "\n")
            
        print(f"Cell finished in {dur:.1f}s with exit_code {exit_code}")

print("\nAll signal_and_routing runs complete!")
