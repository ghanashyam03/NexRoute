"""
Unit tests for Publication-Ready Visualization Pipeline.
Constructs synthetic in-memory DataFrames matching real schemas and asserts output figures and tables
are generated with correct file existence, non-zero size, and exact percent-change arithmetic.
"""

import sys
import pytest
from pathlib import Path
import pandas as pd

# Add repository root to sys.path so 'experiments' package is importable
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from experiments.visualize_results import (
    generate_summary_results_table,
    visualize_results,
    get_significance_marker
)


def test_significance_marker():
    """Verify p-value to significance marker conversion."""
    assert get_significance_marker(0.0001) == "***"
    assert get_significance_marker(0.005) == "**"
    assert get_significance_marker(0.03) == "*"
    assert get_significance_marker(0.15) == "ns"


def test_generate_summary_results_table_arithmetic(tmp_path):
    """Verify summary table percent-change calculation against a hand-computed arithmetic example."""
    # Scenario: grid_test, Metric: avg_waiting_time
    # Baseline mean = 20.0, Combined mean = 10.0 -> Change = (10 - 20) / 20 * 100 = -50.0%
    agg_records = []
    for s in range(1, 6):
        agg_records.append({"scenario": "grid_test", "seed": s, "condition": "baseline", "avg_waiting_time": 20.0})
        agg_records.append({"scenario": "grid_test", "seed": s, "condition": "combined", "avg_waiting_time": 10.0})

    df_agg = pd.DataFrame(agg_records)

    stats_records = [{
        "scenario": "grid_test",
        "metric": "avg_waiting_time",
        "comparison_pair": "combined_vs_baseline",
        "condition_a": "combined",
        "condition_b": "baseline",
        "test_type": "paired_ttest",
        "statistic": -15.0,
        "p_value": 0.0001,
        "p_value_adj_fdr": 0.0005,
        "effect_size_cohen_d": -5.0,
        "ci_lower_95": -10.5,
        "ci_upper_95": -9.5,
        "n_pairs": 5,
        "caution_flag": "use_with_caution_small_n"
    }]
    df_stats = pd.DataFrame(stats_records)

    out_dir = tmp_path / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_df = generate_summary_results_table(df_agg, df_stats, out_dir)

    assert len(summary_df) == 1
    row = summary_df.iloc[0]

    assert row["Scenario"] == "grid_test"
    assert row["Metric"] == "avg_waiting_time"
    assert row["Baseline Mean"] == 20.0
    assert row["Combined Mean"] == 10.0
    assert row["Change (%)"] == -50.0  # Exact -50.0% reduction
    assert row["p_value_adj_fdr"] == 0.0005
    assert row["Significance"] == "***"

    # Verify CSV and TeX files generated with non-zero size
    csv_file = out_dir / "summary_results_table.csv"
    tex_file = out_dir / "summary_results_table.tex"
    assert csv_file.exists() and csv_file.stat().st_size > 0
    assert tex_file.exists() and tex_file.stat().st_size > 0

    # Read TeX content and verify LaTeX syntax
    tex_content = tex_file.read_text(encoding="utf-8")
    assert "\\begin{table}" in tex_content
    assert "-50.00\\%" in tex_content


def test_visualize_results_end_to_end(tmp_path):
    """Verify visualize_results generates all box plots, forest plots, synergy bar charts, and summary tables."""
    agg_records = []
    for cond in ["baseline", "signal_only", "vsl_only", "routing_only", "combined"]:
        for s in range(1, 6):
            val = 20.0 if cond == "baseline" else (15.0 if cond != "combined" else 10.0)
            agg_records.append({
                "scenario": "synth_sc",
                "seed": s,
                "condition": cond,
                "avg_waiting_time": val,
                "avg_speed": 10.0 + (5.0 if cond == "combined" else 0.0)
            })

    df_agg = pd.DataFrame(agg_records)
    parquet_file = tmp_path / "aggregated_results.parquet"
    df_agg.to_parquet(parquet_file, index=False)

    stats_records = []
    pairs = [
        "signal_only_vs_baseline", "vsl_only_vs_baseline", "routing_only_vs_baseline", "combined_vs_baseline",
        "signal_only_vs_vsl_only", "signal_only_vs_routing_only", "vsl_only_vs_routing_only",
        "combined_vs_signal_only", "combined_vs_vsl_only", "combined_vs_routing_only"
    ]
    for m in ["avg_waiting_time", "avg_speed"]:
        for p in pairs:
            stats_records.append({
                "scenario": "synth_sc",
                "metric": m,
                "comparison_pair": p,
                "condition_a": p.split("_vs_")[0],
                "condition_b": p.split("_vs_")[1],
                "test_type": "paired_ttest",
                "statistic": -5.0,
                "p_value": 0.001,
                "p_value_adj_fdr": 0.002,
                "effect_size_cohen_d": -2.5,
                "ci_lower_95": -3.0,
                "ci_upper_95": -2.0,
                "n_pairs": 5,
                "caution_flag": "use_with_caution_small_n"
            })

    df_stats = pd.DataFrame(stats_records)
    stats_csv_file = tmp_path / "statistical_analysis.csv"
    df_stats.to_csv(stats_csv_file, index=False)

    out_dir = tmp_path / "figures"

    visualize_results(
        input_parquet=parquet_file,
        input_stats_csv=stats_csv_file,
        output_dir=out_dir,
        key_metrics=["avg_waiting_time", "avg_speed"]
    )

    expected_files = [
        out_dir / "synth_sc_avg_waiting_time_boxplot.png",
        out_dir / "synth_sc_avg_waiting_time_boxplot.pdf",
        out_dir / "synth_sc_avg_waiting_time_forestplot.png",
        out_dir / "synth_sc_avg_waiting_time_forestplot.pdf",
        out_dir / "synth_sc_avg_speed_boxplot.png",
        out_dir / "synth_sc_avg_speed_boxplot.pdf",
        out_dir / "synth_sc_avg_speed_forestplot.png",
        out_dir / "synth_sc_avg_speed_forestplot.pdf",
        out_dir / "synth_sc_synergy_summary.png",
        out_dir / "synth_sc_synergy_summary.pdf",
        out_dir / "summary_results_table.csv",
        out_dir / "summary_results_table.tex",
    ]

    for f_path in expected_files:
        assert f_path.exists(), f"Expected file '{f_path}' was not generated."
        assert f_path.stat().st_size > 0, f"Generated file '{f_path}' is empty."
