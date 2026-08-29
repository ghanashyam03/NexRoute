"""
NexRoute Statistical Hypothesis Testing & Effect Size Analysis Pipeline.

Reads `experiments/results/aggregated_results.parquet`, performs seed-aligned paired t-tests
and Wilcoxon signed-rank tests across baseline and non-baseline condition pairs per scenario,
computes Cohen's d effect sizes and 95% bootstrap confidence intervals, applies Benjamini-Hochberg
FDR multiple-comparisons correction per scenario, and outputs long-format statistical results to CSV.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
import scipy.stats as stats

logger = logging.getLogger(__name__)

# All 8 ablation conditions
DEFAULT_CONDITIONS = [
    "baseline", "signal_only", "vsl_only", "routing_only",
    "signal_and_routing", "signal_and_vsl", "vsl_and_routing", "combined"
]

# Comparison pairs (Condition A vs Condition B)
COMPARISON_PAIRS: List[Tuple[str, str, str]] = [
    # 1. Baseline comparisons
    ("signal_only", "baseline", "signal_only_vs_baseline"),
    ("vsl_only", "baseline", "vsl_only_vs_baseline"),
    ("routing_only", "baseline", "routing_only_vs_baseline"),
    ("signal_and_routing", "baseline", "signal_and_routing_vs_baseline"),
    ("signal_and_vsl", "baseline", "signal_and_vsl_vs_baseline"),
    ("vsl_and_routing", "baseline", "vsl_and_routing_vs_baseline"),
    ("combined", "baseline", "combined_vs_baseline"),
    # 2. Key dual-component vs single-component comparisons
    ("signal_and_routing", "signal_only", "signal_and_routing_vs_signal_only"),
    ("signal_and_routing", "routing_only", "signal_and_routing_vs_routing_only"),
    ("signal_and_routing", "combined", "signal_and_routing_vs_combined"),
    # 3. Pairwise among non-baseline components
    ("signal_only", "vsl_only", "signal_only_vs_vsl_only"),
    ("signal_only", "routing_only", "signal_only_vs_routing_only"),
    ("vsl_only", "routing_only", "vsl_only_vs_routing_only"),
    # 4. Synergistic combined vs individual components
    ("combined", "signal_only", "combined_vs_signal_only"),
    ("combined", "vsl_only", "combined_vs_vsl_only"),
    ("combined", "routing_only", "combined_vs_routing_only"),
]


def benjamini_hochberg_fdr(p_values: np.ndarray) -> np.ndarray:
    """
    Compute Benjamini-Hochberg False Discovery Rate (FDR) adjusted p-values.

    Args:
        p_values: 1D numpy array of raw p-values.

    Returns:
        1D numpy array of adjusted p-values (q-values) bounded in [0.0, 1.0].
    """
    pvals = np.asarray(p_values, dtype=float)
    m = len(pvals)
    if m == 0:
        return np.array([], dtype=float)
    if m == 1:
        return np.clip(pvals, 0.0, 1.0)

    # Sort p-values in ascending order
    sort_idx = np.argsort(pvals)
    sorted_pvals = pvals[sort_idx]

    # Calculate unadjusted BH values: q = p * m / rank (1-indexed rank)
    ranks = np.arange(1, m + 1, dtype=float)
    q_vals = sorted_pvals * (m / ranks)

    # Enforce monotonicity from right to left (backwards cumulative minimum)
    q_vals = np.minimum.accumulate(q_vals[::-1])[::-1]

    # Clip to max 1.0
    q_vals = np.clip(q_vals, 0.0, 1.0)

    # Re-map adjusted p-values back to original input array indices
    adjusted_pvals = np.empty_like(q_vals)
    adjusted_pvals[sort_idx] = q_vals

    return adjusted_pvals


def compute_cohens_d(diffs: np.ndarray) -> float:
    """
    Compute Cohen's d effect size for paired differences: d = mean(diffs) / std(diffs).
    Returns 0.0 if standard deviation is 0.
    """
    if len(diffs) < 2:
        return 0.0
    mean_diff = np.mean(diffs)
    std_diff = np.std(diffs, ddof=1)
    if std_diff == 0.0 or np.isnan(std_diff):
        return 0.0
    return float(mean_diff / std_diff)


def compute_bootstrap_ci(
    diffs: np.ndarray,
    n_bootstraps: int = 10000,
    ci_level: float = 0.95,
    random_seed: int = 42
) -> Tuple[float, float]:
    """
    Compute percentile bootstrap confidence interval for mean paired difference.
    """
    n = len(diffs)
    if n == 0:
        return 0.0, 0.0

    rng = np.random.default_rng(seed=random_seed)
    boot_means = np.empty(n_bootstraps, dtype=float)
    
    for b in range(n_bootstraps):
        boot_sample = rng.choice(diffs, size=n, replace=True)
        boot_means[b] = np.mean(boot_sample)

    alpha_half = (1.0 - ci_level) / 2.0 * 100.0
    ci_lower = float(np.percentile(boot_means, alpha_half))
    ci_upper = float(np.percentile(boot_means, 100.0 - alpha_half))

    return ci_lower, ci_upper


def run_paired_comparison(
    vals_a: np.ndarray,
    vals_b: np.ndarray,
    test_type: str
) -> Tuple[float, float]:
    """
    Execute paired statistical test ('paired_ttest' or 'wilcoxon_signed_rank').
    
    Returns:
        (statistic, p_value)
    """
    diffs = vals_a - vals_b

    if test_type == "paired_ttest":
        if np.all(diffs == 0.0):
            return 0.0, 1.0
        try:
            res = stats.ttest_rel(vals_a, vals_b)
            stat = float(res.statistic) if not np.isnan(res.statistic) else 0.0
            pval = float(res.pvalue) if not np.isnan(res.pvalue) else 1.0
            return stat, pval
        except Exception:
            return 0.0, 1.0

    elif test_type == "wilcoxon_signed_rank":
        if np.all(diffs == 0.0):
            return 0.0, 1.0
        try:
            res = stats.wilcoxon(vals_a, vals_b)
            stat = float(res.statistic) if not np.isnan(res.statistic) else 0.0
            pval = float(res.pvalue) if not np.isnan(res.pvalue) else 1.0
            return stat, pval
        except Exception:
            return 0.0, 1.0
    else:
        raise ValueError(f"Unknown test type '{test_type}'")


def analyze_aggregated_results(
    input_parquet: Path,
    output_csv: Path,
    min_pairs: int = 3,
    n_bootstraps: int = 10000,
    metric_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Load aggregated results dataframe, execute paired tests and effect sizes for all scenario metrics,
    apply Benjamini-Hochberg FDR correction per scenario, and write results CSV.
    """
    input_path = Path(input_parquet).resolve()
    out_path = Path(output_csv).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Aggregated results file not found at: {input_path}")

    df = pd.read_parquet(input_path)
    if df.empty:
        raise ValueError("Input dataset is empty.")

    # Identify numerical metric columns if not specified
    if metric_cols is None:
        exclude_cols = {"scenario", "seed", "condition", "exit_code", "success", "duration_seconds"}
        metric_cols = [
            c for c in df.columns
            if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])
        ]

    logger.info(f"Analyzing {len(metric_cols)} metric(s) across scenarios: {df['scenario'].unique().tolist()}")

    scenarios = sorted(df["scenario"].unique().tolist())
    all_results = []

    for sc in scenarios:
        df_sc = df[df["scenario"] == sc]
        scenario_records = []

        for col in metric_cols:
            for cond_a, cond_b, pair_name in COMPARISON_PAIRS:
                df_a = df_sc[df_sc["condition"] == cond_a]
                df_b = df_sc[df_sc["condition"] == cond_b]

                if df_a.empty or df_b.empty:
                    continue

                # Align paired samples strictly by seed
                common_seeds = sorted(list(set(df_a["seed"]).intersection(set(df_b["seed"]))))
                n_pairs = len(common_seeds)

                if n_pairs < min_pairs:
                    logger.warning(
                        f"Skipping pair comparison: scenario='{sc}', metric='{col}', pair='{pair_name}'. "
                        f"Only {n_pairs} paired seed(s) available (minimum required: {min_pairs})."
                    )
                    continue

                # Extract aligned values
                vals_a = np.array([df_a[df_a["seed"] == s][col].values[0] for s in common_seeds], dtype=float)
                vals_b = np.array([df_b[df_b["seed"] == s][col].values[0] for s in common_seeds], dtype=float)
                diffs = vals_a - vals_b

                # Effect size and bootstrap confidence interval
                cohen_d = compute_cohens_d(diffs)
                ci_low, ci_high = compute_bootstrap_ci(diffs, n_bootstraps=n_bootstraps)

                caution_flag = "use_with_caution_small_n" if n_pairs < 10 else "none"

                # Perform both paired t-test and Wilcoxon signed-rank test
                for test_type in ["paired_ttest", "wilcoxon_signed_rank"]:
                    stat, pval = run_paired_comparison(vals_a, vals_b, test_type)

                    rec = {
                        "scenario": sc,
                        "metric": col,
                        "comparison_pair": pair_name,
                        "condition_a": cond_a,
                        "condition_b": cond_b,
                        "test_type": test_type,
                        "statistic": stat,
                        "p_value": pval,
                        "p_value_adj_fdr": pval,  # Will be updated by FDR correction per scenario
                        "effect_size_cohen_d": cohen_d,
                        "ci_lower_95": ci_low,
                        "ci_upper_95": ci_high,
                        "n_pairs": n_pairs,
                        "caution_flag": caution_flag
                    }
                    scenario_records.append(rec)

        # Apply Benjamini-Hochberg FDR correction across ALL p-values for this scenario
        if scenario_records:
            raw_pvals = np.array([r["p_value"] for r in scenario_records], dtype=float)
            adj_pvals = benjamini_hochberg_fdr(raw_pvals)
            for idx, r in enumerate(scenario_records):
                r["p_value_adj_fdr"] = float(adj_pvals[idx])
            all_results.extend(scenario_records)

    if not all_results:
        logger.warning("No valid paired comparisons could be performed.")
        res_df = pd.DataFrame(columns=[
            "scenario", "metric", "comparison_pair", "condition_a", "condition_b",
            "test_type", "statistic", "p_value", "p_value_adj_fdr", "effect_size_cohen_d",
            "ci_lower_95", "ci_upper_95", "n_pairs", "caution_flag"
        ])
    else:
        res_df = pd.DataFrame(all_results)

    # Write output long-format CSV
    res_df.to_csv(out_path, index=False)
    logger.info(f"Wrote statistical analysis report: '{out_path}' ({len(res_df)} rows)")

    print("\n" + "=" * 70)
    print("Statistical Analysis Execution Summary")
    print("=" * 70)
    print(f"Input Parquet:           '{input_path}'")
    print(f"Output Statistical CSV:  '{out_path}'")
    print(f"Total Comparisons Run:   {len(res_df):6d}")
    print(f"Scenarios Analyzed:      {len(scenarios):6d}")
    print("=" * 70 + "\n")

    return res_df


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Perform Paired Statistical Hypothesis Testing, Effect Size, and FDR Analysis on NexRoute Results"
    )
    parser.add_argument(
        "--input-parquet",
        type=str,
        default="experiments/results/aggregated_results.parquet",
        help="Path to aggregated results parquet dataset (default: 'experiments/results/aggregated_results.parquet')"
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="experiments/results/statistical_analysis.csv",
        help="Path to output statistical analysis CSV (default: 'experiments/results/statistical_analysis.csv')"
    )
    parser.add_argument(
        "--min-pairs",
        type=int,
        default=3,
        help="Minimum required seed pairs per comparison cell (default: 3)"
    )
    parser.add_argument(
        "--n-bootstraps",
        type=int,
        default=10000,
        help="Number of bootstrap resamples for 95%% CI estimation (default: 10000)"
    )
    return parser.parse_args(args)


def main(args=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parsed = parse_args(args)

    analyze_aggregated_results(
        input_parquet=Path(parsed.input_parquet),
        output_csv=Path(parsed.output_csv),
        min_pairs=parsed.min_pairs,
        n_bootstraps=parsed.n_bootstraps
    )


if __name__ == "__main__":
    main()
