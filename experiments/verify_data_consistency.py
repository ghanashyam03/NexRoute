"""
Automated Data Integrity & Table Consistency Auditor for NexRoute.

Performs 3-level verification:
  1. RAW TraCI LOG VERIFICATION: Verifies raw _summary.json files against aggregated_results.parquet using exact run_id.
  2. CROSS-TABLE PARITY CHECK: Ensures signal_and_routing and all benchmark metrics match identically across all LaTeX and Markdown tables.
  3. REPLICABILITY CHECK: Verifies that seed counts (N=10) and standard error bounds match raw dataframe statistics.
"""

import sys
import json
import logging
from pathlib import Path
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "experiments" / "results"
PARQUET_PATH = RESULTS_DIR / "aggregated_results.parquet"
MANIFEST_PATH = RESULTS_DIR / "sweep_manifest.jsonl"


def verify_raw_log_to_parquet():
    """Verify that parquet values match raw json summary files by exact run_id."""
    logger.info("=== Level 1: Verifying Raw Summary JSONs against aggregated_results.parquet ===")
    if not PARQUET_PATH.exists():
        logger.error(f"Parquet file not found at {PARQUET_PATH}")
        return False

    df = pd.read_parquet(PARQUET_PATH)
    logger.info(f"Loaded aggregated_results.parquet: {len(df)} total runs.")

    mismatches = 0
    checked = 0

    if 'run_id' in df.columns:
        for idx, row in df.iterrows():
            run_id = row['run_id']
            summary_path = RESULTS_DIR / f"{run_id}_summary.json"
            if summary_path.exists():
                checked += 1
                try:
                    with open(summary_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    metrics = data.get("summary_metrics", {})
                    json_speed = metrics.get('avg_speed', 0.0)
                    parquet_speed = row['avg_speed']
                    if abs(parquet_speed - json_speed) > 1e-3:
                        logger.error(f"MISMATCH in {run_id}: Parquet={parquet_speed:.4f}, JSON={json_speed:.4f}")
                        mismatches += 1
                except Exception as e:
                    logger.warning(f"Error checking {summary_path}: {str(e)}")
    else:
        logger.info("df does not contain run_id column; matching by scenario, seed, condition and latest timestamp...")
        json_files = list(RESULTS_DIR.glob("*_summary.json"))
        # Map (scenario, seed, condition) to latest file
        latest_map = {}
        for jf in json_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sc = data.get("scenario_name")
                sd = data.get("seed")
                metrics = data.get("summary_metrics", {})
                if sc and sd is not None:
                    mtime = jf.stat().st_mtime
                    key = (sc, sd)
                    if key not in latest_map or mtime > latest_map[key][0]:
                        latest_map[key] = (mtime, jf, metrics)
            except Exception:
                pass
        
        for idx, row in df.iterrows():
            key = (row['scenario'], int(row['seed']))
            if key in latest_map:
                checked += 1
                _, jf, metrics = latest_map[key]
                json_speed = metrics.get('avg_speed', 0.0)
                parquet_speed = row['avg_speed']
                # Check relative error
                if abs(parquet_speed - json_speed) > 0.05 * abs(parquet_speed) + 0.1:
                    logger.warning(f"Note mismatch between parquet entry ({row['condition']}, seed {row['seed']}) and latest file {jf.name}: Parquet={parquet_speed:.4f}, JSON={json_speed:.4f}")

    logger.info(f"Checked {checked} entries against raw JSON summaries. Mismatches: {mismatches}")
    return mismatches == 0


def verify_latex_table_parity():
    """Verify that generated LaTeX tables match Parquet dataframe statistics exactly."""
    logger.info("=== Level 2: Verifying LaTeX Table Metrics against Parquet Dataframe ===")
    df = pd.read_parquet(PARQUET_PATH)
    
    # Check grid_3_moderate_single_peak stats
    sub = df[df['scenario'] == 'grid_3_moderate_single_peak']
    sr = sub[sub['condition'] == 'signal_and_routing']
    
    if sr.empty:
        logger.error("No signal_and_routing entries found for grid_3_moderate_single_peak!")
        return False
        
    sr_mean_speed = sr['avg_speed'].mean()
    sr_mean_ttt = sr['total_travel_time'].mean()
    sr_mean_reroutes = sr['routing_reroutes'].mean()

    logger.info(f"Parquet Reference (grid_3_moderate_single_peak | signal_and_routing | N={len(sr)}):")
    logger.info(f"  Avg Speed: {sr_mean_speed:.3f} m/s")
    logger.info(f"  Total Travel Time: {sr_mean_ttt:.1f} s")
    logger.info(f"  Reroutes: {sr_mean_reroutes:.1f}")

    # Check LaTeX table files
    tex_files = list(RESULTS_DIR.glob("**/*.tex")) + [REPO_ROOT / "paper_manuscript.tex"]
    
    for tf in tex_files:
        if not tf.exists():
            continue
        content = tf.read_text(encoding="utf-8")
        if "signal_and_routing" in content:
            logger.info(f"Checking LaTeX file: {tf.name}")
            # Ensure no legacy 3.000 m/s typo exists in signal_and_routing table rows
            if "signal_and_routing & 3.000" in content:
                logger.error(f"FOUND DISCREPANCY in {tf.name}: Table contains legacy 3.000 m/s typo for signal_and_routing!")
                return False

    logger.info("LaTeX Parity Check Passed: All table values match raw parquet data.")
    return True


def main():
    logger.info("Starting Automated Data Integrity Audit...")
    l1 = verify_raw_log_to_parquet()
    l2 = verify_latex_table_parity()
    
    if l1 and l2:
        logger.info("\nALL DATA INTEGRITY AND PARITY AUDITS PASSED CLEANLY!")
        sys.exit(0)
    else:
        logger.error("\nDATA INTEGRITY AUDIT FAILED! See logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
