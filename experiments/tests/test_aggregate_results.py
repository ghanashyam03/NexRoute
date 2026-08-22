"""
Unit tests for Ablation Results Aggregator.
Uses sample_sweep_manifest.jsonl fixture to test parsing, completeness, warnings, and parquet export.
"""

import sys
import pytest
from pathlib import Path
import pandas as pd

# Add repository root to sys.path so 'experiments' package is importable
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from experiments.aggregate_results import (
    load_and_parse_manifest,
    validate_manifest_completeness,
    check_seed_counts_per_cell,
    aggregate_results
)


def get_fixture_manifest_path() -> Path:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "sample_sweep_manifest.jsonl"
    return fixture_path


def test_load_and_parse_manifest_shape_and_dtypes():
    """Verify loading the fixture manifest produces a clean DataFrame with proper columns and dtypes."""
    fixture_path = get_fixture_manifest_path()
    assert fixture_path.exists()

    df = load_and_parse_manifest(fixture_path)

    # 5 total rows in fixture (4 successes, 1 failure)
    assert len(df) == 5

    # Check required columns
    required_cols = ["scenario", "seed", "condition", "exit_code", "success", "duration_seconds", "avg_speed"]
    for col in required_cols:
        assert col in df.columns

    # Verify dtypes
    assert df["scenario"].dtype == object or df["scenario"].dtype == "string"
    assert df["seed"].dtype == "int64" or df["seed"].dtype == "int32"
    assert df["condition"].dtype == object or df["condition"].dtype == "string"
    assert df["exit_code"].dtype == "int64" or df["exit_code"].dtype == "int32"
    assert df["success"].dtype == bool
    assert df["duration_seconds"].dtype == "float64"

    # Verify success boolean derivation
    assert bool(df.loc[df["seed"] == 1, "success"].iloc[0]) is True
    # Row 5 (seed 2, signal_only) failed
    failed_row = df[(df["seed"] == 2) & (df["condition"] == "signal_only")]
    assert bool(failed_row["success"].iloc[0]) is False
    assert failed_row["exit_code"].iloc[0] == 1


def test_validate_manifest_completeness():
    """Verify that missing and failed combinations are correctly detected and reported."""
    fixture_path = get_fixture_manifest_path()
    df = load_and_parse_manifest(fixture_path)

    expected_scenarios = ["grid_3_light"]
    expected_seeds = [1, 2, 3]
    expected_conditions = ["baseline", "signal_only"]

    missing, failed = validate_manifest_completeness(
        df,
        expected_scenarios=expected_scenarios,
        expected_seeds=expected_seeds,
        expected_conditions=expected_conditions
    )

    # Failed combination: (grid_3_light, 2, signal_only)
    assert ("grid_3_light", 2, "signal_only") in failed

    # Missing combination: (grid_3_light, 3, signal_only)
    assert ("grid_3_light", 3, "signal_only") in missing
    assert ("grid_3_light", 1, "baseline") not in missing
    assert ("grid_3_light", 1, "baseline") not in failed


def test_low_seed_count_warning():
    """Verify that cells with fewer successful seeds than min_seeds_per_cell are flagged."""
    fixture_path = get_fixture_manifest_path()
    df = load_and_parse_manifest(fixture_path)
    df_success = df[df["success"] == True]

    expected_scenarios = ["grid_3_light"]
    expected_conditions = ["baseline", "signal_only"]

    sparse_cells = check_seed_counts_per_cell(
        df_success,
        min_seeds_per_cell=3,
        expected_scenarios=expected_scenarios,
        expected_conditions=expected_conditions
    )

    # baseline has 3 successful seeds (1, 2, 3) -> NOT sparse
    # signal_only has only 1 successful seed (seed 1) -> SPARSE (< 3)
    sparse_cell_names = [(sc, cond) for sc, cond, cnt in sparse_cells]
    assert ("grid_3_light", "signal_only") in sparse_cell_names
    assert ("grid_3_light", "baseline") not in sparse_cell_names


def test_aggregate_results_end_to_end(tmp_path):
    """Verify aggregate_results writes analysis-ready Parquet and preview CSV files for successful rows."""
    fixture_path = get_fixture_manifest_path()
    out_dir = tmp_path / "results"

    df_out = aggregate_results(
        input_manifest=fixture_path,
        output_dir=out_dir,
        expected_scenarios=["grid_3_light"],
        expected_seeds=[1, 2, 3],
        expected_conditions=["baseline", "signal_only"],
        min_seeds_per_cell=3
    )

    # 4 successful rows in fixture
    assert len(df_out) == 4

    parquet_file = out_dir / "aggregated_results.parquet"
    csv_file = out_dir / "aggregated_results_preview.csv"

    assert parquet_file.exists()
    assert csv_file.exists()

    # Read back exported parquet file and verify schema/contents
    df_parquet = pd.read_parquet(parquet_file)
    assert len(df_parquet) == 4
    assert "avg_speed" in df_parquet.columns
    assert (df_parquet["success"] == True).all()

    # Read back exported CSV file
    df_csv = pd.read_csv(csv_file)
    assert len(df_csv) == 4
