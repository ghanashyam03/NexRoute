"""
Unit tests for Paired Statistical Analysis Pipeline.
Uses synthetic in-memory pandas DataFrames to verify paired t-tests, Wilcoxon signed-rank tests,
Cohen's d effect sizes, bootstrap confidence intervals, and Benjamini-Hochberg FDR adjustments.
"""

import sys
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

# Add repository root to sys.path so 'experiments' package is importable
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from experiments.analyze_results import (
    benjamini_hochberg_fdr,
    compute_cohens_d,
    compute_bootstrap_ci,
    analyze_aggregated_results
)


def test_benjamini_hochberg_fdr_math():
    """Verify Benjamini-Hochberg FDR function produces mathematically exact adjusted p-values."""
    raw_pvals = np.array([0.001, 0.01, 0.04, 0.20])
    adj_pvals = benjamini_hochberg_fdr(raw_pvals)

    # Expected: [0.004, 0.02, 0.05333333, 0.20]
    expected = np.array([0.004, 0.02, 0.05333333, 0.20])
    np.testing.assert_allclose(adj_pvals, expected, rtol=1e-4)


def test_cohens_d_and_bootstrap_ci():
    """Verify Cohen's d effect size and bootstrap CI math on synthetic paired differences."""
    diffs = np.array([10.0, 10.2, 9.8, 10.1, 9.9])
    d = compute_cohens_d(diffs)

    # Mean = 10.0, std = 0.1581 -> d = 10.0 / 0.1581 ≈ 63.24
    assert d > 50.0

    ci_low, ci_high = compute_bootstrap_ci(diffs, n_bootstraps=1000, random_seed=42)
    assert 9.5 <= ci_low <= 10.1
    assert 9.9 <= ci_high <= 10.5


def test_known_large_effect_fixture(tmp_path):
    """Verify hypothesis testing on a synthetic fixture with a known, large true effect (10 units waiting time reduction)."""
    rng = np.random.default_rng(42)
    seeds = list(range(1, 11))  # 10 seeds
    records = []

    for s in seeds:
        noise = float(rng.normal(0, 0.1))
        # baseline avg_waiting_time = ~20.0
        records.append({
            "scenario": "test_synth",
            "seed": s,
            "condition": "baseline",
            "exit_code": 0,
            "success": True,
            "duration_seconds": 1.0,
            "avg_waiting_time": 20.0 + noise
        })
        # combined avg_waiting_time = ~10.0 (10 units lower)
        records.append({
            "scenario": "test_synth",
            "seed": s,
            "condition": "combined",
            "exit_code": 0,
            "success": True,
            "duration_seconds": 1.0,
            "avg_waiting_time": 10.0 + noise
        })

    df = pd.DataFrame(records)
    parquet_path = tmp_path / "aggregated_results.parquet"
    csv_path = tmp_path / "statistical_analysis.csv"
    df.to_parquet(parquet_path, index=False)

    res_df = analyze_aggregated_results(
        input_parquet=parquet_path,
        output_csv=csv_path,
        n_bootstraps=1000
    )

    assert not res_df.empty
    comb_vs_base = res_df[
        (res_df["comparison_pair"] == "combined_vs_baseline") &
        (res_df["test_type"] == "paired_ttest")
    ]
    assert len(comb_vs_base) == 1
    row = comb_vs_base.iloc[0]

    # p-value must be extremely small (< 0.001)
    assert row["p_value"] < 0.001
    assert row["p_value_adj_fdr"] < 0.001
    # Mean difference (combined - baseline) = -10.0
    assert row["effect_size_cohen_d"] < -20.0
    assert -10.5 <= row["ci_lower_95"] <= -9.5
    assert -10.5 <= row["ci_upper_95"] <= -9.5


def test_null_effect_fixture(tmp_path):
    """Verify hypothesis testing on a synthetic fixture with NO true effect (pure noise) yields non-significant p-value."""
    rng = np.random.default_rng(123)
    seeds = list(range(1, 11))
    records = []

    for s in seeds:
        noise_a = float(rng.normal(0, 1.0))
        noise_b = float(rng.normal(0, 1.0))
        records.append({
            "scenario": "test_null",
            "seed": s,
            "condition": "baseline",
            "exit_code": 0,
            "success": True,
            "duration_seconds": 1.0,
            "avg_speed": 12.0 + noise_a
        })
        records.append({
            "scenario": "test_null",
            "seed": s,
            "condition": "signal_only",
            "exit_code": 0,
            "success": True,
            "duration_seconds": 1.0,
            "avg_speed": 12.0 + noise_b
        })

    df = pd.DataFrame(records)
    parquet_path = tmp_path / "aggregated_results.parquet"
    csv_path = tmp_path / "statistical_analysis.csv"
    df.to_parquet(parquet_path, index=False)

    res_df = analyze_aggregated_results(
        input_parquet=parquet_path,
        output_csv=csv_path,
        n_bootstraps=1000
    )

    sig_vs_base = res_df[
        (res_df["comparison_pair"] == "signal_only_vs_baseline") &
        (res_df["test_type"] == "paired_ttest")
    ]
    assert len(sig_vs_base) == 1
    row = sig_vs_base.iloc[0]

    # Null effect must NOT be spuriously significant (p > 0.05)
    assert row["p_value"] > 0.05


def test_small_sample_caution_flag_and_skip(tmp_path):
    """Verify that n < 3 pairs are skipped and n < 10 pairs receive the caution flag."""
    records = []
    # Seed 1..5 for baseline
    for s in range(1, 6):
        records.append({"scenario": "sparse", "seed": s, "condition": "baseline", "avg_speed": 10.0})
        records.append({"scenario": "sparse", "seed": s, "condition": "vsl_only", "avg_speed": 10.5})

    # Only Seed 1 & 2 for combined -> n = 2 (< 3 min_pairs) for combined vs vsl_only
    for s in [1, 2]:
        records.append({"scenario": "sparse", "seed": s, "condition": "combined", "avg_speed": 11.0})

    df = pd.DataFrame(records)
    parquet_path = tmp_path / "aggregated_results.parquet"
    csv_path = tmp_path / "statistical_analysis.csv"
    df.to_parquet(parquet_path, index=False)

    res_df = analyze_aggregated_results(
        input_parquet=parquet_path,
        output_csv=csv_path,
        min_pairs=3,
        n_bootstraps=500
    )

    # combined_vs_baseline (n=2) was skipped!
    assert res_df[res_df["comparison_pair"] == "combined_vs_baseline"].empty

    # vsl_only_vs_baseline (n=5) has caution_flag == 'use_with_caution_small_n'
    vsl_row = res_df[res_df["comparison_pair"] == "vsl_only_vs_baseline"].iloc[0]
    assert vsl_row["caution_flag"] == "use_with_caution_small_n"
    assert vsl_row["n_pairs"] == 5
