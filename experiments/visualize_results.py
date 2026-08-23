"""
NexRoute Publication-Ready Experiment Visualization & Table Generator.

Reads aggregated results (parquet) and statistical analysis (CSV) to generate:
  1. Grouped box plots per scenario and key metric (comparing distributions across 5 conditions).
  2. Forest plots showing Cohen's d effect sizes with 95% CIs and low-power (small n) flags.
  3. Synergy summary bar charts comparing Combined against the Best Single Component.
  4. Publication summary results table exported as both CSV and LaTeX tabular (.tex).
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless figure generation
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Standard 5 ablation conditions
DEFAULT_CONDITIONS = ["baseline", "signal_only", "vsl_only", "routing_only", "combined"]

# Publication Palette
CONDITION_COLORS = {
    "baseline": "#4C72B0",      # Slate steel blue
    "signal_only": "#DD8452",   # Coral orange
    "vsl_only": "#55A868",      # Sage green
    "routing_only": "#C44E52",  # Crimson red
    "combined": "#8172B3"       # Deep purple
}

# Metrics where lower values represent better performance
LOWER_IS_BETTER_METRICS = {
    "avg_waiting_time", "total_travel_time", "system_congestion",
    "predicted_congestion", "total_stops", "avg_trip_duration"
}


def apply_publication_style():
    """Apply clean, publication-grade Matplotlib aesthetic settings."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.8,
        "grid.color": "#CCCCCC",
        "grid.linestyle": "--",
        "grid.alpha": 0.5,
        "figure.titlesize": 12,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "savefig.dpi": 300,
        "savefig.bbox": "tight"
    })


def get_significance_marker(p_val: float) -> str:
    """Return standard academic significance asterisks based on p-value threshold."""
    if p_val < 0.001:
        return "***"
    elif p_val < 0.01:
        return "**"
    elif p_val < 0.05:
        return "*"
    else:
        return "ns"


def plot_grouped_box_plot(
    df: pd.DataFrame,
    scenario: str,
    metric: str,
    output_dir: Path
):
    """
    Generate grouped box plot showing metric distributions across seeds for all 5 conditions.
    Baseline condition is visually distinguished using hatching and distinct borders.
    """
    df_sc = df[df["scenario"] == scenario]
    if df_sc.empty:
        return

    fig, ax = plt.subplots(figsize=(7, 4.5))

    data_by_cond = []
    labels = []
    colors = []

    for cond in DEFAULT_CONDITIONS:
        vals = df_sc[df_sc["condition"] == cond][metric].dropna().values
        if len(vals) > 0:
            data_by_cond.append(vals)
            labels.append(cond.replace("_", "\n").title())
            colors.append(CONDITION_COLORS.get(cond, "#777777"))

    if not data_by_cond:
        plt.close(fig)
        return

    bp = ax.boxplot(
        data_by_cond,
        tick_labels=labels,
        patch_artist=True,
        widths=0.55,
        medianprops=dict(color="black", linewidth=1.2),
        flierprops=dict(marker="o", markersize=4, alpha=0.6)
    )

    # Style individual box colors and apply hatch pattern to baseline
    for idx, (patch, cond) in enumerate(zip(bp["boxes"], DEFAULT_CONDITIONS)):
        patch.set_facecolor(CONDITION_COLORS.get(cond, "#777777"))
        patch.set_alpha(0.85)
        if cond == "baseline":
            patch.set_hatch("//")
            patch.set_edgecolor("#111111")
            patch.set_linewidth(1.5)
        else:
            patch.set_edgecolor("#333333")
            patch.set_linewidth(1.0)

    ax.set_ylabel(metric.replace("_", " ").title())
    ax.set_title(f"Condition Performance Distribution: {scenario.replace('_', ' ').title()} ({metric.replace('_', ' ')})")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    out_png = output_dir / f"{scenario}_{metric}_boxplot.png"
    out_pdf = output_dir / f"{scenario}_{metric}_boxplot.pdf"
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)
    logger.info(f"Saved box plot: '{out_png}'")


def plot_forest_plot(
    df_stats: pd.DataFrame,
    scenario: str,
    metric: str,
    output_dir: Path
):
    """
    Generate forest plot showing Cohen's d effect sizes and 95% CIs per comparison pair.
    Visually flags rows where caution_flag == 'use_with_caution_small_n'.
    """
    df_sub = df_stats[
        (df_stats["scenario"] == scenario) &
        (df_stats["metric"] == metric) &
        (df_stats["test_type"] == "paired_ttest")
    ].copy()

    if df_sub.empty:
        return

    # Sort comparisons logically
    df_sub = df_sub.sort_values(by="comparison_pair", ascending=False)
    n_rows = len(df_sub)

    fig, ax = plt.subplots(figsize=(8, max(4.0, n_rows * 0.45)))

    y_positions = np.arange(n_rows)

    for idx, (_, row) in enumerate(df_sub.iterrows()):
        y_pos = y_positions[idx]
        d_val = row["effect_size_cohen_d"]
        ci_low = row["ci_lower_95"]
        ci_high = row["ci_upper_95"]
        caution = row["caution_flag"]
        p_adj = row["p_value_adj_fdr"]
        sig_str = get_significance_marker(p_adj)

        is_sparse = (caution == "use_with_caution_small_n")

        # Color and marker styling based on sample size power flag
        color = "#D95F02" if is_sparse else "#2B5C8F"
        marker = "d" if is_sparse else "o"
        linestyle = "--" if is_sparse else "-"

        # Plot error bar CI line
        ax.errorbar(
            x=d_val,
            y=y_pos,
            xerr=[[d_val - ci_low], [ci_high - d_val]],
            fmt=marker,
            color=color,
            ecolor=color,
            elinewidth=1.5 if not is_sparse else 1.2,
            capsize=4,
            capthick=1.2,
            markersize=6 if not is_sparse else 7,
            linestyle=linestyle
        )

        # Annotate p-value and significance
        ax.text(
            ci_high + 0.15,
            y_pos,
            f"d={d_val:.2f} {sig_str}" + (" [Low n]" if is_sparse else ""),
            va="center",
            ha="left",
            fontsize=8.5,
            color=color,
            fontweight="bold" if is_sparse else "normal"
        )

    # Reference line at zero effect
    ax.axvline(x=0.0, color="black", linestyle=":", linewidth=1.2, alpha=0.7)

    labels = [r["comparison_pair"].replace("_", " ").title() for _, r in df_sub.iterrows()]
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Cohen's d Effect Size (Paired Difference) with 95% CI")
    ax.set_title(f"Forest Plot of Effect Sizes: {scenario.replace('_', ' ').title()} ({metric.replace('_', ' ')})")
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    out_png = output_dir / f"{scenario}_{metric}_forestplot.png"
    out_pdf = output_dir / f"{scenario}_{metric}_forestplot.pdf"
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)
    logger.info(f"Saved forest plot: '{out_png}'")


def plot_synergy_bar_chart(
    df: pd.DataFrame,
    scenario: str,
    output_dir: Path,
    key_metrics: List[str]
):
    """
    Generate summary bar chart comparing 'Combined' against the single Best Component
    per metric for a given scenario.
    """
    df_sc = df[df["scenario"] == scenario]
    if df_sc.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 4.5))

    metrics_plotted = []
    best_single_names = []
    best_single_vals = []
    combined_vals = []
    baseline_vals = []

    for metric in key_metrics:
        if metric not in df_sc.columns:
            continue

        base_val = df_sc[df_sc["condition"] == "baseline"][metric].mean()
        comb_val = df_sc[df_sc["condition"] == "combined"][metric].mean()

        if np.isnan(base_val) or np.isnan(comb_val):
            continue

        # Single components pool
        single_conds = ["signal_only", "vsl_only", "routing_only"]
        single_means = {}
        for c in single_conds:
            c_val = df_sc[df_sc["condition"] == c][metric].mean()
            if not np.isnan(c_val):
                single_means[c] = c_val

        if not single_means:
            continue

        # Dynamically determine best single component based on metric direction
        if metric in LOWER_IS_BETTER_METRICS:
            best_cond = min(single_means, key=single_means.get)
        else:
            best_cond = max(single_means, key=single_means.get)

        best_val = single_means[best_cond]

        metrics_plotted.append(metric.replace("_", "\n").title())
        best_single_names.append(best_cond.replace("_only", "").upper())
        best_single_vals.append(best_val)
        combined_vals.append(comb_val)
        baseline_vals.append(base_val)

    if not metrics_plotted:
        plt.close(fig)
        return

    x = np.arange(len(metrics_plotted))
    width = 0.25

    rects1 = ax.bar(x - width, baseline_vals, width, label="Baseline", color="#4C72B0", hatch="//", alpha=0.85)
    rects2 = ax.bar(x, best_single_vals, width, label="Best Single Component", color="#DD8452", alpha=0.85)
    rects3 = ax.bar(x + width, combined_vals, width, label="Combined Optimization", color="#8172B3", alpha=0.85)

    # Annotate bars with percentage improvement of Combined over Best Single
    for idx in range(len(metrics_plotted)):
        b_val = best_single_vals[idx]
        c_val = combined_vals[idx]
        if b_val != 0.0:
            pct_change = ((c_val - b_val) / b_val) * 100.0
            sign = "+" if pct_change > 0 else ""
            ax.text(
                x[idx] + width,
                c_val * 1.02,
                f"{sign}{pct_change:.1f}%",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                color="#8172B3"
            )

    ax.set_xticks(x)
    ax.set_xticklabels(metrics_plotted)
    ax.set_ylabel("Metric Value")
    ax.set_title(f"Synergy Evaluation: Combined vs. Best Single Component ({scenario.replace('_', ' ').title()})")
    ax.legend(frameon=True, facecolor="white", edgecolor="#CCCCCC")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    out_png = output_dir / f"{scenario}_synergy_summary.png"
    out_pdf = output_dir / f"{scenario}_synergy_summary.pdf"
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)
    logger.info(f"Saved synergy bar chart: '{out_png}'")


def generate_summary_results_table(
    df_agg: pd.DataFrame,
    df_stats: pd.DataFrame,
    output_dir: Path
) -> pd.DataFrame:
    """
    Generate paper-ready summary table comparing Baseline vs Combined performance per scenario and metric.
    Exports summary_results_table.csv and renders summary_results_table.tex LaTeX tabular snippet.
    """
    table_rows = []

    scenarios = sorted(df_agg["scenario"].unique().tolist())
    exclude_cols = {"scenario", "seed", "condition", "exit_code", "success", "duration_seconds"}
    metrics = [c for c in df_agg.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df_agg[c])]

    for sc in scenarios:
        df_sc_agg = df_agg[df_agg["scenario"] == sc]

        for m in metrics:
            base_vals = df_sc_agg[df_sc_agg["condition"] == "baseline"][m].dropna()
            comb_vals = df_sc_agg[df_sc_agg["condition"] == "combined"][m].dropna()

            if base_vals.empty or comb_vals.empty:
                continue

            base_mean = float(base_vals.mean())
            comb_mean = float(comb_vals.mean())

            pct_change = ((comb_mean - base_mean) / base_mean * 100.0) if base_mean != 0.0 else 0.0

            # Retrieve adjusted p-value from statistical_analysis.csv for combined_vs_baseline
            stat_match = df_stats[
                (df_stats["scenario"] == sc) &
                (df_stats["metric"] == m) &
                (df_stats["comparison_pair"] == "combined_vs_baseline") &
                (df_stats["test_type"] == "paired_ttest")
            ]

            if not stat_match.empty:
                p_adj = float(stat_match["p_value_adj_fdr"].iloc[0])
            else:
                p_adj = 1.0

            sig_marker = get_significance_marker(p_adj)

            table_rows.append({
                "Scenario": sc,
                "Metric": m,
                "Baseline Mean": round(base_mean, 3),
                "Combined Mean": round(comb_mean, 3),
                "Change (%)": round(pct_change, 2),
                "p_value_adj_fdr": round(p_adj, 4),
                "Significance": sig_marker
            })

    summary_df = pd.DataFrame(table_rows)

    # 1. Export CSV
    csv_path = output_dir / "summary_results_table.csv"
    summary_df.to_csv(csv_path, index=False)
    logger.info(f"Wrote summary results CSV table: '{csv_path}'")

    # 2. Export LaTeX Tabular Snippet (.tex)
    tex_path = output_dir / "summary_results_table.tex"
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("% Auto-generated NexRoute Paper Results Table\n")
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write("\\caption{Summary of NexRoute Ablation Results: Baseline vs. Combined Optimization}\n")
        f.write("\\label{tab:nexroute_results_summary}\n")
        f.write("\\begin{tabular}{l l r r r r l}\n")
        f.write("\\hline\n")
        f.write("\\textbf{Scenario} & \\textbf{Metric} & \\textbf{Baseline} & \\textbf{Combined} & \\textbf{Change (\\%)} & \\textbf{$p_{\\text{adj}}$} & \\textbf{Sig.} \\\\\n")
        f.write("\\hline\n")

        for _, r in summary_df.iterrows():
            sc_clean = str(r['Scenario']).replace('_', '\\_')
            m_clean = str(r['Metric']).replace('_', '\\_')
            change_str = f"{r['Change (%)']:+.2f}\\%"
            p_str = f"{r['p_value_adj_fdr']:.4f}" if r['p_value_adj_fdr'] >= 0.0001 else "<0.0001"
            f.write(f"{sc_clean} & {m_clean} & {r['Baseline Mean']:.3f} & {r['Combined Mean']:.3f} & {change_str} & {p_str} & {r['Significance']} \\\\\n")

        f.write("\\hline\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")

    logger.info(f"Wrote summary results LaTeX table: '{tex_path}'")
    return summary_df


def visualize_results(
    input_parquet: Path,
    input_stats_csv: Path,
    output_dir: Path,
    key_metrics: Optional[List[str]] = None
):
    """
    Main visualization pipeline generating box plots, forest plots, synergy bar charts, and summary tables.
    """
    apply_publication_style()

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df_agg = pd.read_parquet(input_parquet)
    df_stats = pd.read_csv(input_stats_csv)

    if key_metrics is None:
        key_metrics = ["avg_waiting_time", "total_travel_time", "avg_speed", "completed_trips"]

    scenarios = sorted(df_agg["scenario"].unique().tolist())

    for sc in scenarios:
        for m in key_metrics:
            if m in df_agg.columns:
                # 1. Grouped box plots
                plot_grouped_box_plot(df_agg, sc, m, out_dir)
                # 2. Forest plots
                plot_forest_plot(df_stats, sc, m, out_dir)

        # 3. Synergy summary bar chart per scenario
        plot_synergy_bar_chart(df_agg, sc, out_dir, key_metrics)

    # 4. Summary table generation (.csv and .tex)
    generate_summary_results_table(df_agg, df_stats, out_dir)

    print("\n" + "=" * 70)
    print("Visualization & Table Generation Complete")
    print("=" * 70)
    print(f"Output Directory: '{out_dir}'")
    print(f"Figures & Tables Generated for {len(scenarios)} Scenario(s)")
    print("=" * 70 + "\n")


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Generate Publication-Ready Figures and Tables for NexRoute Experiment Sweep"
    )
    parser.add_argument(
        "--input-parquet",
        type=str,
        default="experiments/results/aggregated_results.parquet",
        help="Path to aggregated results parquet file (default: 'experiments/results/aggregated_results.parquet')"
    )
    parser.add_argument(
        "--input-stats-csv",
        type=str,
        default="experiments/results/statistical_analysis.csv",
        help="Path to statistical analysis CSV file (default: 'experiments/results/statistical_analysis.csv')"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/results/figures",
        help="Target output directory for generated figures and tables (default: 'experiments/results/figures')"
    )
    parser.add_argument(
        "--metrics",
        type=str,
        default="avg_waiting_time,total_travel_time,avg_speed,completed_trips",
        help="Comma-separated list of metrics to visualize (default: 'avg_waiting_time,total_travel_time,avg_speed,completed_trips')"
    )
    return parser.parse_args(args)


def main(args=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parsed = parse_args(args)

    metrics_list = [m.strip() for m in parsed.metrics.split(",") if m.strip()]

    visualize_results(
        input_parquet=Path(parsed.input_parquet),
        input_stats_csv=Path(parsed.input_stats_csv),
        output_dir=Path(parsed.output_dir),
        key_metrics=metrics_list
    )


if __name__ == "__main__":
    main()
