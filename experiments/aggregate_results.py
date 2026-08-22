"""
NexRoute Experiment Results Aggregator and Data Cleaner.

Reads `sweep_manifest.jsonl`, flattens summary metrics into a clean, typed, tabular dataset,
performs completeness and sanity validation, flags low-seed-count cells, and exports:
  1. experiments/results/aggregated_results.parquet (typed, analysis-ready binary format)
  2. experiments/results/aggregated_results_preview.csv (human-readable CSV preview)
"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Standard 5 ablation conditions
DEFAULT_CONDITIONS = ["baseline", "signal_only", "vsl_only", "routing_only", "combined"]


def flatten_summary_metrics(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten summary metrics dictionary and cast any NumPy scalar types to standard Python primitives.
    Handles nested 'final_metrics' or direct top-level metric keys.
    """
    flat: Dict[str, Any] = {}
    if not isinstance(summary, dict):
        return flat

    # Extract metrics from 'final_metrics' nested dict if present
    metrics_source = summary.get("final_metrics", summary)
    if not isinstance(metrics_source, dict):
        metrics_source = summary

    for k, v in metrics_source.items():
        if isinstance(v, (dict, list)):
            continue
        # Convert NumPy types (e.g. np.float64, np.int64) to native Python types
        if isinstance(v, (np.floating, float)):
            flat[k] = float(v)
        elif isinstance(v, (np.integer, int)):
            flat[k] = int(v)
        elif isinstance(v, (np.bool_, bool)):
            flat[k] = bool(v)
        else:
            flat[k] = v

    return flat


def load_and_parse_manifest(manifest_path: Path) -> pd.DataFrame:
    """
    Parse sweep_manifest.jsonl into a flattened Pandas DataFrame.
    
    Columns: scenario, seed, condition, exit_code, duration_seconds, success, plus summary metrics.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Sweep manifest file not found at: {manifest_path}")

    records = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as err:
                logger.warning(f"Skipping malformed JSON on line {line_num} in '{manifest_path}': {err}")
                continue

            scenario = str(data.get("scenario", ""))
            seed = int(data.get("seed", 0)) if data.get("seed") is not None else 0
            condition = str(data.get("condition", ""))
            exit_code = int(data.get("exit_code", 1))
            success = bool(exit_code == 0)
            duration_sec = float(data.get("duration_seconds", 0.0)) if data.get("duration_seconds") is not None else 0.0

            row = {
                "scenario": scenario,
                "seed": seed,
                "condition": condition,
                "exit_code": exit_code,
                "success": success,
                "duration_seconds": duration_sec
            }

            # Flatten summary metrics for successful runs
            summary_dict = data.get("summary", {})
            metrics = flatten_summary_metrics(summary_dict)
            
            for m_key, m_val in metrics.items():
                row[m_key] = m_val

            records.append(row)

    if not records:
        return pd.DataFrame(columns=["scenario", "seed", "condition", "exit_code", "success", "duration_seconds"])

    df = pd.DataFrame(records)
    
    # Enforce strict column dtypes
    df["scenario"] = df["scenario"].astype(str)
    df["seed"] = df["seed"].astype(int)
    df["condition"] = df["condition"].astype(str)
    df["exit_code"] = df["exit_code"].astype(int)
    df["success"] = df["success"].astype(bool)
    df["duration_seconds"] = df["duration_seconds"].astype(float)

    return df


def validate_manifest_completeness(
    df: pd.DataFrame,
    expected_scenarios: Optional[List[str]] = None,
    expected_seeds: Optional[List[int]] = None,
    expected_conditions: Optional[List[str]] = None
) -> Tuple[List[Tuple[str, int, str]], List[Tuple[str, int, str]]]:
    """
    Check dataset completeness against expected scenarios, seeds, and conditions.
    
    Returns:
        (missing_combinations, failed_combinations)
    """
    if expected_scenarios is None:
        expected_scenarios = sorted(df["scenario"].unique().tolist()) if not df.empty else []
    if expected_seeds is None:
        expected_seeds = sorted(df["seed"].unique().tolist()) if not df.empty else []
    if expected_conditions is None:
        expected_conditions = DEFAULT_CONDITIONS

    # Build set of expected (scenario, seed, condition) tuples
    expected_set = {
        (sc, sd, cond)
        for sc in expected_scenarios
        for sd in expected_seeds
        for cond in expected_conditions
    }

    # Map present records from DataFrame
    present_set = set()
    successful_set = set()
    failed_set = set()

    if not df.empty:
        for _, row in df.iterrows():
            cell = (row["scenario"], int(row["seed"]), row["condition"])
            present_set.add(cell)
            if row["success"]:
                successful_set.add(cell)
            else:
                failed_set.add(cell)

    missing_combinations = sorted(list(expected_set - present_set))
    failed_combinations = sorted(list(failed_set))

    # Print clear, explicit summary reports
    print("\n" + "-" * 70)
    print("Sweep Manifest Completeness & Failure Report")
    print("-" * 70)
    print(f"Total Expected Combinations: {len(expected_set)}")
    print(f"Present in Manifest:        {len(present_set)}")
    print(f"  - Successful Runs:        {len(successful_set)}")
    print(f"  - Failed Runs:            {len(failed_combinations)}")
    print(f"Missing Entirely:           {len(missing_combinations)}")

    if failed_combinations:
        print("\n[WARNING] Failed Combinations (exit_code != 0):")
        for sc, sd, cond in failed_combinations:
            print(f"  - Scenario: '{sc}', Seed: {sd}, Condition: '{cond}'")

    if missing_combinations:
        print("\n[WARNING] Missing Combinations (not in manifest):")
        for sc, sd, cond in missing_combinations:
            print(f"  - Scenario: '{sc}', Seed: {sd}, Condition: '{cond}'")

    print("-" * 70 + "\n")

    return missing_combinations, failed_combinations


def check_seed_counts_per_cell(
    df_success: pd.DataFrame,
    min_seeds_per_cell: int = 3,
    expected_scenarios: Optional[List[str]] = None,
    expected_conditions: Optional[List[str]] = None
) -> List[Tuple[str, str, int]]:
    """
    Check if any (scenario, condition) cell has fewer successful seeds than min_seeds_per_cell.
    Logs loud warnings for sparse cells.
    
    Returns:
        List of (scenario, condition, count) for sparse cells.
    """
    sparse_cells = []
    
    if expected_scenarios is None:
        expected_scenarios = sorted(df_success["scenario"].unique().tolist()) if not df_success.empty else []
    if expected_conditions is None:
        expected_conditions = DEFAULT_CONDITIONS

    for sc in expected_scenarios:
        for cond in expected_conditions:
            cell_df = df_success[(df_success["scenario"] == sc) & (df_success["condition"] == cond)]
            seed_count = cell_df["seed"].nunique()
            if seed_count < min_seeds_per_cell:
                sparse_cells.append((sc, cond, seed_count))
                logger.warning(
                    f"LOW SEED COUNT: Cell (scenario='{sc}', condition='{cond}') "
                    f"has only {seed_count} successful seed(s) (threshold: {min_seeds_per_cell}). "
                    f"Statistical testing on this cell will be underpowered."
                )

    return sparse_cells


def aggregate_results(
    input_manifest: Path,
    output_dir: Path,
    expected_scenarios: Optional[List[str]] = None,
    expected_seeds: Optional[List[int]] = None,
    expected_conditions: Optional[List[str]] = None,
    min_seeds_per_cell: int = 3
) -> pd.DataFrame:
    """
    Full pipeline to load, validate, clean, and export aggregated experiment results.
    
    Outputs:
      - output_dir/aggregated_results.parquet
      - output_dir/aggregated_results_preview.csv
    """
    manifest_path = Path(input_manifest).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df_all = load_and_parse_manifest(manifest_path)

    # 1. Validate completeness & report missing/failed runs
    missing_cells, failed_cells = validate_manifest_completeness(
        df_all,
        expected_scenarios=expected_scenarios,
        expected_seeds=expected_seeds,
        expected_conditions=expected_conditions
    )

    # 2. Filter successful runs only for downstream statistical analysis
    df_success = df_all[df_all["success"] == True].copy() # noqa: E712

    # 3. Check minimum seed counts per cell
    sparse_cells = check_seed_counts_per_cell(
        df_success,
        min_seeds_per_cell=min_seeds_per_cell,
        expected_scenarios=expected_scenarios,
        expected_conditions=expected_conditions
    )

    # 4. Export Parquet and CSV files
    parquet_path = out_dir / "aggregated_results.parquet"
    csv_preview_path = out_dir / "aggregated_results_preview.csv"

    # Export Parquet
    df_success.to_parquet(parquet_path, index=False)
    logger.info(f"Wrote analysis-ready Parquet dataset: '{parquet_path}' ({len(df_success)} rows, {len(df_success.columns)} columns)")

    # Export CSV Preview
    df_success.to_csv(csv_preview_path, index=False)
    logger.info(f"Wrote human-readable CSV preview: '{csv_preview_path}'")

    print("=" * 70)
    print("Results Aggregation Complete")
    print("=" * 70)
    print(f"Input Manifest:          '{manifest_path}'")
    print(f"Successful Rows Cleaned: {len(df_success)} / {len(df_all)}")
    print(f"Parquet Dataset:         '{parquet_path}'")
    print(f"CSV Preview:             '{csv_preview_path}'")
    if sparse_cells:
        print(f"Sparse Cells Warning:    {len(sparse_cells)} cell(s) have < {min_seeds_per_cell} seeds")
    print("=" * 70 + "\n")

    return df_success


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Aggregate and Clean NexRoute Ablation Sweep Results into Parquet & CSV Datasets"
    )
    parser.add_argument(
        "--input-manifest",
        type=str,
        default="experiments/results/sweep_manifest.jsonl",
        help="Path to input sweep_manifest.jsonl (default: 'experiments/results/sweep_manifest.jsonl')"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/results",
        help="Directory to write aggregated output files (default: 'experiments/results')"
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default=None,
        help="Comma-separated expected scenarios for completeness check (default: inferred from data)"
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default=None,
        help="Comma-separated expected integer seeds (e.g. '1,2,3,4,5')"
    )
    parser.add_argument(
        "--conditions",
        type=str,
        default=None,
        help="Comma-separated expected conditions (default: 5 standard research conditions)"
    )
    parser.add_argument(
        "--min-seeds-per-cell",
        type=int,
        default=3,
        help="Minimum required successful seed threshold per cell (default: 3)"
    )
    return parser.parse_args(args)


def main(args=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parsed = parse_args(args)

    scenarios = [s.strip() for s in parsed.scenarios.split(",") if s.strip()] if parsed.scenarios else None
    seeds = [int(s.strip()) for s in parsed.seeds.split(",") if s.strip()] if parsed.seeds else None
    conditions = [c.strip() for c in parsed.conditions.split(",") if c.strip()] if parsed.conditions else None

    aggregate_results(
        input_manifest=Path(parsed.input_manifest),
        output_dir=Path(parsed.output_dir),
        expected_scenarios=scenarios,
        expected_seeds=seeds,
        expected_conditions=conditions,
        min_seeds_per_cell=parsed.min_seeds_per_cell
    )


if __name__ == "__main__":
    main()
