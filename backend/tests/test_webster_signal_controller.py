"""
Unit Tests for Webster's Optimal Signal Controller Baseline
"""

import pytest
from backend.app.baselines.webster_signal_controller import (
    compute_cycle_length,
    compute_green_splits
)
from backend.app.signal_strategies import WebsterSignalController


def test_webster_hand_computed_example():
    """
    Hand-Computed Verification Example:
    -----------------------------------
    Number of phases: N = 2
    Lost time per phase: l = 4.0 s
    Total lost time: L = 2 * 4.0 = 8.0 s

    Phase 1 critical flow ratio: y_1 = 0.25
    Phase 2 critical flow ratio: y_2 = 0.35
    Total critical flow ratio: Y = y_1 + y_2 = 0.25 + 0.35 = 0.60

    Optimal Cycle Length (Webster 1958):
        C_opt = (1.5 * L + 5) / (1 - Y)
              = (1.5 * 8.0 + 5) / (1.0 - 0.60)
              = (12.0 + 5.0) / 0.40
              = 17.0 / 0.40
              = 42.5 seconds

    Total Effective Green Time:
        G_total = C_opt - L
                = 42.5 - 8.0
                = 34.5 seconds

    Phase Green Splits:
        g_1 = G_total * (y_1 / Y)
            = 34.5 * (0.25 / 0.60)
            = 34.5 * (5 / 12)
            = 14.375 seconds

        g_2 = G_total * (y_2 / Y)
            = 34.5 * (0.35 / 0.60)
            = 34.5 * (7 / 12)
            = 20.125 seconds
    """
    critical_flow_ratios = [0.25, 0.35]
    lost_time_per_phase = 4.0
    total_lost_time = 2 * lost_time_per_phase

    cycle_len = compute_cycle_length(
        critical_flow_ratios=critical_flow_ratios,
        lost_time_per_phase=lost_time_per_phase,
        min_cycle=30.0,
        max_cycle=120.0
    )
    assert cycle_len == pytest.approx(42.5, abs=1e-5)

    green_splits = compute_green_splits(
        cycle_length=cycle_len,
        critical_flow_ratios=critical_flow_ratios,
        total_lost_time=total_lost_time,
        min_green=5.0
    )
    assert len(green_splits) == 2
    assert green_splits[0] == pytest.approx(14.375, abs=1e-5)
    assert green_splits[1] == pytest.approx(20.125, abs=1e-5)


def test_webster_oversaturated_clamping():
    """Verify that Y >= 0.95 clamps optimal cycle length to max_cycle."""
    critical_flow_ratios = [0.50, 0.50]  # Y = 1.0 >= 0.95
    cycle_len = compute_cycle_length(
        critical_flow_ratios=critical_flow_ratios,
        lost_time_per_phase=4.0,
        min_cycle=30.0,
        max_cycle=120.0
    )
    assert cycle_len == 120.0

    green_splits = compute_green_splits(
        cycle_length=cycle_len,
        critical_flow_ratios=critical_flow_ratios,
        total_lost_time=8.0,
        min_green=5.0
    )
    assert green_splits == [56.0, 56.0]


def test_webster_undersaturated_clamping():
    """Verify that low flow clamps optimal cycle length to min_cycle."""
    critical_flow_ratios = [0.05, 0.05]  # Y = 0.10 -> C_opt = 17 / 0.9 = 18.89s
    cycle_len = compute_cycle_length(
        critical_flow_ratios=critical_flow_ratios,
        lost_time_per_phase=4.0,
        min_cycle=30.0,
        max_cycle=120.0
    )
    assert cycle_len == 30.0

    green_splits = compute_green_splits(
        cycle_length=cycle_len,
        critical_flow_ratios=critical_flow_ratios,
        total_lost_time=8.0,
        min_green=5.0
    )
    assert green_splits == [11.0, 11.0]


def test_webster_signal_controller_class():
    """Verify WebsterSignalController strategy class wrapper."""
    controller = WebsterSignalController(
        lost_time_per_phase=4.0,
        min_green=5.0,
        max_green=100.0,
        saturation_flow=1800.0
    )

    traffic_data = {
        'phase_flows': [450.0, 630.0]  # 450/1800 = 0.25, 630/1800 = 0.35
    }
    splits = controller.compute_phase_durations('signal_1', traffic_data)
    assert len(splits) == 2
    assert splits[0] == pytest.approx(14.375, abs=1e-5)
    assert splits[1] == pytest.approx(20.125, abs=1e-5)
