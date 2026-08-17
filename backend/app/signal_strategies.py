"""
Signal Control Strategy Abstraction and Implementations.

Defines the SignalControlStrategy abstract base class and concrete controllers:
- WebsterSignalController: Fixed-time baseline using Webster's (1958) optimal timing formula.
- PSOSignalController: Dynamic PSO-based adaptive signal optimization.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

from .baselines.webster_signal_controller import compute_cycle_length, compute_green_splits

logger = logging.getLogger(__name__)


class SignalControlStrategy(ABC):
    """Abstract Base Class for traffic signal control strategies."""

    @abstractmethod
    def compute_phase_durations(
        self,
        signal_id: str,
        traffic_data: Dict[str, Any]
    ) -> List[float]:
        """
        Compute phase green durations for a given traffic signal junction.

        Args:
            signal_id: The ID of the traffic signal junction.
            traffic_data: Dictionary containing phase flows, controlled lanes, metrics, etc.

        Returns:
            List of phase green durations in seconds.
        """
        pass


class WebsterSignalController(SignalControlStrategy):
    """Fixed-time baseline signal controller based on Webster's (1958) optimal timing formula."""

    def __init__(
        self,
        lost_time_per_phase: float = 4.0,
        min_green: float = 5.0,
        max_green: float = 100.0,
        saturation_flow: float = 1800.0  # vehicles per hour per lane
    ):
        self.lost_time_per_phase = lost_time_per_phase
        self.min_green = min_green
        self.max_green = max_green
        self.saturation_flow = saturation_flow

    def compute_phase_durations(
        self,
        signal_id: str,
        traffic_data: Dict[str, Any]
    ) -> List[float]:
        """
        Compute phase green durations using Webster's formula based on phase critical flow ratios.
        """
        if 'critical_flow_ratios' in traffic_data:
            ratios = traffic_data['critical_flow_ratios']
        else:
            phase_flows = traffic_data.get('phase_flows', [])
            ratios = [max(0.0, f / self.saturation_flow) for f in phase_flows]

        if not ratios:
            return []

        num_phases = len(ratios)
        total_lost_time = num_phases * self.lost_time_per_phase

        cycle_len = compute_cycle_length(
            critical_flow_ratios=ratios,
            lost_time_per_phase=self.lost_time_per_phase,
            min_cycle=num_phases * self.min_green + total_lost_time,
            max_cycle=num_phases * self.max_green + total_lost_time
        )

        green_splits = compute_green_splits(
            cycle_length=cycle_len,
            critical_flow_ratios=ratios,
            total_lost_time=total_lost_time,
            min_green=self.min_green
        )

        clamped_splits = [max(self.min_green, min(self.max_green, g)) for g in green_splits]
        return clamped_splits


class PSOSignalController(SignalControlStrategy):
    """Dynamic PSO-based signal controller strategy."""

    def __init__(self, base_green_time: float = 35.0, min_green: float = 20.0, max_green: float = 100.0):
        self.base_green_time = base_green_time
        self.min_green = min_green
        self.max_green = max_green

    def compute_phase_durations(
        self,
        signal_id: str,
        traffic_data: Dict[str, Any]
    ) -> List[float]:
        """
        Compute phase green durations using PSO optimization parameters.
        """
        params = traffic_data.get('params', [self.base_green_time, 1.2, 0.6])
        base_green_time, demand_weight, queue_weight = params
        phase_demands = traffic_data.get('phase_demands', [])
        phase_queues = traffic_data.get('phase_queues', [])

        durations = []
        num_phases = max(len(phase_demands), len(phase_queues))
        for i in range(num_phases):
            demand = phase_demands[i] if i < len(phase_demands) else 0.0
            queue = phase_queues[i] if i < len(phase_queues) else 0.0
            duration = base_green_time + (demand / 500.0) * demand_weight + queue * queue_weight * 2.5
            clamped = max(self.min_green, min(self.max_green, duration))
            durations.append(clamped)

        return durations
