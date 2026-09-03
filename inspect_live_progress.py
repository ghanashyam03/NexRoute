import time
from pathlib import Path
import pandas as pd

results_dir = Path("experiments/results")

json_files = list(results_dir.glob("*_summary.json"))
csv_files = list(results_dir.glob("*_timeseries.csv"))
p1 = results_dir / "vsl_harmonization_manifest.jsonl"
p2 = results_dir / "threshold_sensitivity_manifest.jsonl"

now = time.time()

recently_modified_json = [f for f in json_files if (now - f.stat().st_mtime) < 14400] # modified in last 4 hours
recently_modified_csv = [f for f in csv_files if (now - f.stat().st_mtime) < 14400]

print(f"Total Summary JSONs in results: {len(json_files)}")
print(f"Summary JSONs created/modified in last 4 hours: {len(recently_modified_json)}")
print(f"Time-series CSVs created/modified in last 4 hours: {len(recently_modified_csv)}")

if p1.exists():
    df1 = pd.read_json(p1, lines=True)
    print(f"\nVSL Harmonization Manifest: {len(df1)} total entries.")
    print("Latest 3 entries in VSL Manifest:")
    print(df1.tail(3)[['scenario', 'vsl_min_speed', 'seed', 'avg_speed']])

if p2.exists():
    df2 = pd.read_json(p2, lines=True)
    print(f"\nThreshold Sensitivity Manifest: {len(df2)} total entries.")
    print("Latest 3 entries in Threshold Manifest:")
    print(df2.tail(3)[['scenario', 'routing_threshold', 'seed', 'avg_speed']])
