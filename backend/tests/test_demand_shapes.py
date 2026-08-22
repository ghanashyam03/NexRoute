"""
Unit tests for demand profile shapes math and route file merging logic.
Pure Python math tests — no SUMO dependency required.
"""

import pytest
from pathlib import Path
import xml.etree.ElementTree as ET
from backend.scenario_tools.demand_shapes import (
    flat_profile,
    single_peak_profile,
    two_peak_profile,
    get_demand_profile,
    merge_and_sort_route_files,
    BASE_DEMAND_PERIODS
)


def test_flat_profile():
    """Verify flat_profile produces a single interval spanning the full duration."""
    intervals = flat_profile("moderate", duration=3600.0)
    assert len(intervals) == 1
    start_t, end_t, period = intervals[0]
    assert start_t == 0.0
    assert end_t == 3600.0
    assert period == BASE_DEMAND_PERIODS["moderate"]


def test_single_peak_profile():
    """Verify single_peak_profile vehicle departure rate at peak_time_fraction exceeds rates at t=0 and t=duration."""
    duration = 3600.0
    intervals = single_peak_profile("moderate", duration=duration, peak_time_fraction=0.5, num_intervals=12)
    assert len(intervals) == 12

    # Calculate arrival rates (vehicles / sec = 1 / period)
    rates = [1.0 / period for (_, _, period) in intervals]

    # Peak index for 50% fraction is index 5 or 6 (middle of 12 intervals)
    peak_idx = len(rates) // 2

    # Rate at peak must strictly exceed rate at start (t=0) and end (t=duration)
    assert rates[peak_idx] > rates[0]
    assert rates[peak_idx] > rates[-1]


def test_two_peak_profile_two_local_maxima():
    """Verify two_peak_profile math produces two distinct local maxima (morning and evening peaks)."""
    duration = 3600.0
    intervals = two_peak_profile("moderate", duration=duration, num_intervals=20)
    assert len(intervals) == 20

    rates = [1.0 / period for (_, _, period) in intervals]

    # Split into morning half (0..9) and evening half (10..19)
    morning_rates = rates[:10]
    evening_rates = rates[10:]

    max_morning = max(morning_rates)
    max_evening = max(evening_rates)

    # Morning peak must occur around ~25% (indices 4/5), evening peak around ~75% (indices 14/15)
    morning_peak_idx = rates.index(max_morning)
    evening_peak_idx = rates.index(max_evening)

    assert 3 <= morning_peak_idx <= 6
    assert 13 <= evening_peak_idx <= 16

    # Verify midday valley (between morning and evening peaks) is strictly lower than both peak maxima
    midday_valley = min(rates[morning_peak_idx:evening_peak_idx])
    assert midday_valley < max_morning * 0.5
    assert midday_valley < max_evening * 0.5


def test_get_demand_profile_invalid():
    """Verify get_demand_profile raises ValueError on invalid shape or level."""
    with pytest.raises(ValueError):
        get_demand_profile("unknown_shape", "moderate")

    with pytest.raises(ValueError):
        flat_profile("invalid_level")


def test_merge_and_sort_route_files(tmp_path):
    """Verify merging multiple sub-interval route files preserves depart-time sorting and unique vehicle IDs."""
    f1 = tmp_path / "part1.rou.xml"
    f2 = tmp_path / "part2.rou.xml"
    out = tmp_path / "merged.rou.xml"

    # Part 1: Vehicles departing at 10.0 and 30.0
    f1.write_text("""<routes>
        <vType id="car" vClass="passenger"/>
        <vehicle id="v0_1" depart="10.00"><route edges="e1 e2"/></vehicle>
        <vehicle id="v0_2" depart="30.00"><route edges="e1 e2"/></vehicle>
    </routes>""", encoding="utf-8")

    # Part 2: Vehicles departing at 5.0 and 20.0 (out of order relative to part 1)
    f2.write_text("""<routes>
        <vType id="car" vClass="passenger"/>
        <vehicle id="v1_1" depart="5.00"><route edges="e1 e2"/></vehicle>
        <vehicle id="v1_2" depart="20.00"><route edges="e1 e2"/></vehicle>
    </routes>""", encoding="utf-8")

    merge_and_sort_route_files([f1, f2], out)

    assert out.exists()
    tree = ET.parse(out)
    root = tree.getroot()

    vehicles = root.findall("vehicle")
    assert len(vehicles) == 4

    departs = [float(v.attrib["depart"]) for v in vehicles]
    assert departs == [5.0, 10.0, 20.0, 30.0]  # Strictly sorted

    veh_ids = [v.attrib["id"] for v in vehicles]
    assert len(set(veh_ids)) == 4  # Unique IDs
