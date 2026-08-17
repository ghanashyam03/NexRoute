"""
Webster's Optimal Signal Timing Controller

Implements F.V. Webster's (1958) classic formula for fixed-time traffic signal optimization.

Reference:
    Webster, F.V. (1958). "Traffic Signal Settings". Road Research Technical Paper No. 39.
    H.M. Stationery Office, London.

Formulas:
    1. Optimal Cycle Length:
       C_opt = (1.5 * L + 5) / (1 - Y)
       where:
         L = total lost time per cycle = sum(lost_time_per_phase for each phase)
         Y = sum of critical flow ratios (flow / saturation_flow) for all phases

    2. Total Effective Green Time:
       G_total = C_opt - L

    3. Phase Green Allocation:
       g_i = G_total * (y_i / Y)
       where y_i is the critical flow ratio of phase i.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def compute_cycle_length(
    critical_flow_ratios: List[float],
    lost_time_per_phase: float = 4.0,
    min_cycle: float = 30.0,
    max_cycle: float = 120.0
) -> float:
    """
    Compute Webster's optimal cycle length:
        C_opt = (1.5 * L + 5) / (1 - Y)

    Args:
        critical_flow_ratios: List of critical flow ratios y_i (flow / saturation_flow) for each phase.
        lost_time_per_phase: Lost time per phase in seconds (default: 4.0s).
        min_cycle: Minimum allowable cycle length in seconds (default: 30.0s).
        max_cycle: Maximum allowable cycle length in seconds (default: 120.0s).

    Returns:
        Optimal cycle length C_opt in seconds, bounded within [min_cycle, max_cycle].
    """
    if not critical_flow_ratios:
        return min_cycle

    num_phases = len(critical_flow_ratios)
    total_lost_time = num_phases * lost_time_per_phase
    sum_y = sum(max(0.0, y) for y in critical_flow_ratios)

    # Over-saturated condition or Y >= 0.95: formula denominator approaches zero/negative
    if sum_y >= 0.95:
        logger.warning(
            f"Sum of critical flow ratios Y={sum_y:.3f} >= 0.95 (near/over saturation). "
            f"Clamping cycle length to max_cycle={max_cycle}s."
        )
        return max_cycle

    numerator = 1.5 * total_lost_time + 5.0
    denominator = 1.0 - sum_y

    cycle_opt = numerator / denominator
    return max(min_cycle, min(max_cycle, cycle_opt))


def compute_green_splits(
    cycle_length: float,
    critical_flow_ratios: List[float],
    total_lost_time: float,
    min_green: float = 5.0
) -> List[float]:
    """
    Allocate effective green time proportionally among phases based on critical flow ratios:
        g_i = (C - L) * (y_i / Y)

    Args:
        cycle_length: Total cycle length in seconds (C).
        critical_flow_ratios: List of critical flow ratios y_i for each phase.
        total_lost_time: Total lost time across all phases in seconds (L).
        min_green: Minimum green duration per phase in seconds (default: 5.0s).

    Returns:
        List of green split durations (in seconds) for each phase.
    """
    if not critical_flow_ratios:
        return []

    num_phases = len(critical_flow_ratios)
    effective_green = max(0.0, cycle_length - total_lost_time)
    sum_y = sum(max(0.0, y) for y in critical_flow_ratios)

    if sum_y <= 0:
        # Equal distribution if no flow detected
        equal_green = max(min_green, effective_green / num_phases)
        return [equal_green] * num_phases

    green_splits = []
    for y in critical_flow_ratios:
        y_clamped = max(0.0, y)
        g_i = effective_green * (y_clamped / sum_y)
        g_i = max(min_green, g_i)
        green_splits.append(g_i)

    return green_splits
