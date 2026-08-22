"""
Demand Profile Shapes and Multi-Interval Route Generation Helper for SUMO / NexRoute scenarios.

Provides:
1. Demand profile generators:
   - flat_profile: Constant vehicle arrival rate over duration.
   - single_peak_profile: Sinusoidal bell-curve peak (e.g. rush hour) ramping up and down.
   - two_peak_profile: Commuter morning/evening double-peak shape.
2. Multi-interval demand route file generation and departure-sorted XML merging helper.
"""

import sys
import math
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Base period (seconds per vehicle departure) for flat demand levels
BASE_DEMAND_PERIODS: Dict[str, float] = {
    "light": 2.0,
    "moderate": 1.0,
    "heavy": 0.5
}

# Commuter double-peak constants (Two-peak profile)
# Named, documented constants for commuter morning and evening traffic demand
MORNING_PEAK_FRACTION: float = 0.25  # 25% into duration (e.g. 8 AM in a 24h cycle or t=900s in 3600s)
EVENING_PEAK_FRACTION: float = 0.75  # 75% into duration (e.g. 5 PM in a 24h cycle or t=2700s in 3600s)
MORNING_PEAK_MULTIPLIER: float = 2.5  # 2.5x traffic rate during morning rush hour
EVENING_PEAK_MULTIPLIER: float = 2.2  # 2.2x traffic rate during evening rush hour
OFF_PEAK_MULTIPLIER: float = 0.5      # 0.5x traffic rate during low-demand off-peak hours
VALLEY_MULTIPLIER: float = 0.8        # Midday lull multiplier between morning & evening peaks


def flat_profile(level: str, duration: float = 3600.0) -> List[Tuple[float, float, float]]:
    """
    Flat (constant rate) demand profile spanning [0, duration].
    Preserves backward compatibility with flat light/moderate/heavy demand settings.
    
    Returns:
        List of (start_time, end_time, period_seconds)
    """
    if level not in BASE_DEMAND_PERIODS:
        raise ValueError(f"Invalid demand level '{level}'. Must be one of {list(BASE_DEMAND_PERIODS.keys())}")
    
    period = BASE_DEMAND_PERIODS[level]
    return [(0.0, float(duration), float(period))]


def single_peak_profile(
    level: str,
    duration: float = 3600.0,
    peak_time_fraction: float = 0.5,
    peak_multiplier: float = 2.5,
    num_intervals: int = 12
) -> List[Tuple[float, float, float]]:
    """
    Single-peak demand profile (e.g., event arrival or single rush hour).
    
    Shape Rationale:
    Uses a smooth sinusoidal bell-curve (cosine squared) shape centered around peak_time_fraction.
    Sinusoidal interpolation avoids unrealistic step discontinuities in vehicle departure rates,
    mimicking smooth real-world traffic accumulation and dissipation.
    
    Returns:
        List of (start_time, end_time, period_seconds) across num_intervals.
    """
    if level not in BASE_DEMAND_PERIODS:
        raise ValueError(f"Invalid demand level '{level}'. Must be one of {list(BASE_DEMAND_PERIODS.keys())}")
    
    base_period = BASE_DEMAND_PERIODS[level]
    duration = float(duration)
    interval_dur = duration / num_intervals
    intervals = []
    
    for i in range(num_intervals):
        start_t = i * interval_dur
        end_t = (i + 1) * interval_dur
        mid_t_fraction = (start_t + end_t) / (2.0 * duration)
        
        # Calculate sinusoidal distance factor centered at peak_time_fraction
        dist = abs(mid_t_fraction - peak_time_fraction)
        max_dist = max(peak_time_fraction, 1.0 - peak_time_fraction)
        norm_dist = min(1.0, dist / max_dist)
        
        # Smooth cosine-squared multiplier curve: equals peak_multiplier at peak, 1.0 at edges
        weight = math.cos(norm_dist * (math.pi / 2.0)) ** 2
        multiplier = 1.0 + (peak_multiplier - 1.0) * weight
        
        # Period = base_period / multiplier (higher multiplier -> shorter period -> more vehicles)
        period = base_period / max(0.1, multiplier)
        intervals.append((round(start_t, 2), round(end_t, 2), round(period, 4)))
        
    return intervals


def two_peak_profile(
    level: str,
    duration: float = 3600.0,
    num_intervals: int = 12
) -> List[Tuple[float, float, float]]:
    """
    Two-peak (commuter morning/evening double-peak) demand profile.
    
    Uses named constants MORNING_PEAK_FRACTION, EVENING_PEAK_FRACTION,
    MORNING_PEAK_MULTIPLIER, EVENING_PEAK_MULTIPLIER, and OFF_PEAK_MULTIPLIER
    with a dual Gaussian shape.
    
    Returns:
        List of (start_time, end_time, period_seconds) across num_intervals.
    """
    if level not in BASE_DEMAND_PERIODS:
        raise ValueError(f"Invalid demand level '{level}'. Must be one of {list(BASE_DEMAND_PERIODS.keys())}")
        
    base_period = BASE_DEMAND_PERIODS[level]
    duration = float(duration)
    interval_dur = duration / num_intervals
    intervals = []
    
    # Gaussian standard deviation for peak width (10% of total duration)
    sigma = 0.10
    
    for i in range(num_intervals):
        start_t = i * interval_dur
        end_t = (i + 1) * interval_dur
        mid_t_fraction = (start_t + end_t) / (2.0 * duration)
        
        # Dual Gaussian contribution for morning and evening rush hours
        g_morning = math.exp(-((mid_t_fraction - MORNING_PEAK_FRACTION) ** 2) / (2.0 * (sigma ** 2)))
        g_evening = math.exp(-((mid_t_fraction - EVENING_PEAK_FRACTION) ** 2) / (2.0 * (sigma ** 2)))
        
        # Superimpose morning peak, evening peak, and off-peak baseline
        m_morning_boost = (MORNING_PEAK_MULTIPLIER - OFF_PEAK_MULTIPLIER) * g_morning
        m_evening_boost = (EVENING_PEAK_MULTIPLIER - OFF_PEAK_MULTIPLIER) * g_evening
        
        multiplier = OFF_PEAK_MULTIPLIER + m_morning_boost + m_evening_boost
        
        period = base_period / max(0.1, multiplier)
        intervals.append((round(start_t, 2), round(end_t, 2), round(period, 4)))
        
    return intervals


def get_demand_profile(
    shape: str,
    level: str,
    duration: float = 3600.0
) -> List[Tuple[float, float, float]]:
    """Helper to return interval list for shape name ('flat', 'single_peak', 'two_peak')."""
    if shape == "flat":
        return flat_profile(level, duration)
    elif shape == "single_peak":
        return single_peak_profile(level, duration)
    elif shape == "two_peak":
        return two_peak_profile(level, duration)
    else:
        raise ValueError(f"Unknown demand_shape '{shape}'. Must be one of ['flat', 'single_peak', 'two_peak']")


def generate_demands_for_profile(
    net_file: Path,
    route_file: Path,
    demand_level: str,
    demand_shape: str = "flat",
    duration: float = 3600.0,
    seed: int = None,
    random_trips_py: Path = None,
    extra_args: List[str] = None
) -> None:
    """
    Generate demand route file (.rou.xml) for a given demand shape profile.
    
    Handles multi-interval sub-runs of randomTrips.py and merges the output XMLs
    into a single valid route file strictly sorted by vehicle departure times
    with guaranteed unique vehicle IDs.
    """
    net_path = Path(net_file).resolve()
    route_path = Path(route_file).resolve()
    
    profile_intervals = get_demand_profile(demand_shape, demand_level, duration)
    
    # If flat single-interval demand, run randomTrips.py directly
    if len(profile_intervals) == 1:
        start_t, end_t, period = profile_intervals[0]
        cmd = [
            sys.executable,
            str(random_trips_py),
            "-n", str(net_path),
            "-r", str(route_path),
            "-b", str(start_t),
            "-e", str(end_t),
            "-p", str(period),
            "--fringe-junctions",
            "--validate"
        ]
        if seed is not None:
            cmd.extend(["-s", str(seed)])
        if extra_args:
            cmd.extend(extra_args)
            
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"randomTrips.py failed for flat profile:\n{res.stderr}")
        return

    # Multi-interval generation for peaked profiles
    temp_dir = route_path.parent / f"_temp_trips_{route_path.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    sub_route_files: List[Path] = []
    
    try:
        for idx, (start_t, end_t, period) in enumerate(profile_intervals):
            sub_rou = temp_dir / f"interval_{idx}.rou.xml"
            sub_route_files.append(sub_rou)
            
            # Unique vehicle prefix per sub-interval to eliminate vehicle ID collisions across calls
            veh_prefix = f"v{idx}_"
            
            cmd = [
                sys.executable,
                str(random_trips_py),
                "-n", str(net_path),
                "-r", str(sub_rou),
                "-b", str(start_t),
                "-e", str(end_t),
                "-p", str(period),
                "--prefix", veh_prefix,
                "--fringe-junctions",
                "--validate"
            ]
            if seed is not None:
                # Seed offset per interval for reproducible variation
                cmd.extend(["-s", str(seed + idx)])
            if extra_args:
                cmd.extend(extra_args)
                
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"randomTrips.py failed for interval {idx} [{start_t}s - {end_t}s]:\n{res.stderr}")
        
        # Merge sub-interval route files and sort by depart time
        merge_and_sort_route_files(sub_route_files, route_path)
        
    finally:
        # Cleanup temporary files
        for f in temp_dir.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            temp_dir.rmdir()
        except OSError:
            pass


def merge_and_sort_route_files(input_files: List[Path], output_file: Path) -> None:
    """
    Parse multiple SUMO .rou.xml files, deduplicate <vType> definitions,
    and write a consolidated output file containing all vehicles strictly
    sorted in ascending order by depart attribute.
    """
    vtypes: Dict[str, ET.Element] = {}
    vehicles: List[Tuple[float, ET.Element]] = []
    
    for file_path in input_files:
        if not file_path.exists():
            continue
            
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        for elem in root:
            tag = elem.tag
            if tag == "vType":
                vtype_id = elem.attrib.get("id")
                if vtype_id and vtype_id not in vtypes:
                    vtypes[vtype_id] = elem
            elif tag in ["vehicle", "trip"]:
                depart_str = elem.attrib.get("depart", "0.0")
                try:
                    depart_time = float(depart_str)
                except ValueError:
                    depart_time = 0.0
                vehicles.append((depart_time, elem))
    
    # Strictly sort vehicles by depart time ascending
    vehicles.sort(key=lambda item: item[0])
    
    # Construct output XML root element <routes>
    new_root = ET.Element("routes")
    new_root.text = "\n    "
    
    # 1. Append deduplicated vType elements
    for vtype_elem in vtypes.values():
        new_root.append(vtype_elem)
        
    # 2. Append departure-sorted vehicle elements
    for _, veh_elem in vehicles:
        new_root.append(veh_elem)
        
    # Format XML tree cleanly
    tree_out = ET.ElementTree(new_root)
    ET.indent(tree_out, space="    ", level=0)
    tree_out.write(output_file, encoding="utf-8", xml_declaration=True)
    
    logger.info(
        f"Successfully merged {len(vehicles)} vehicles across {len(input_files)} sub-intervals "
        f"into '{output_file.name}' (strictly sorted by depart time)."
    )
