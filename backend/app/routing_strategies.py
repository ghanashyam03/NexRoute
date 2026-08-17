"""
Routing Strategy Abstraction and Implementations.

Defines the RoutingStrategy abstract base class and concrete routing strategies:
- StaticRoutingStrategy: Static shortest-path baseline (distance/free-flow travel time, no rerouting).
- AdaptiveRoutingStrategy: Dynamic PSO-adaptive routing considering real-time congestion, queues, and predicted delays.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class RoutingStrategy(ABC):
    """Abstract Base Class for traffic routing strategies."""

    @abstractmethod
    def compute_edge_weight(
        self,
        u: str,
        v: str,
        edge_data: Dict[str, Any],
        traffic_metrics: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Compute edge weight for Dijkstra shortest-path routing.

        Args:
            u: Source node ID.
            v: Target node ID.
            edge_data: Dictionary containing edge attributes (e.g. length, speed, lanes).
            traffic_metrics: Optional metrics dictionary for the edge (e.g. avg_speed, queue_length).

        Returns:
            Calculated edge weight (cost) for pathfinding.
        """
        pass

    @abstractmethod
    def should_reroute(
        self,
        vehicle_state: Dict[str, Any],
        traffic_metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine whether a vehicle should be dynamically rerouted mid-trip.

        Args:
            vehicle_state: State dictionary or object for the vehicle.
            traffic_metrics: Optional dictionary of edge traffic metrics.

        Returns:
            True if vehicle should be rerouted, False otherwise.
        """
        pass


class StaticRoutingStrategy(RoutingStrategy):
    """
    Static (non-adaptive) shortest-path routing baseline.

    Uses static free-flow travel time (edge_length / free_flow_speed) without any live
    congestion, queue, or stop penalties. Dynamic mid-trip rerouting is disabled (should_reroute always False).
    """

    def compute_edge_weight(
        self,
        u: str,
        v: str,
        edge_data: Dict[str, Any],
        traffic_metrics: Optional[Dict[str, Any]] = None
    ) -> float:
        length = float(edge_data.get('length', 1.0))
        speed = float(edge_data.get('speed', 13.89))
        if speed <= 0:
            speed = 13.89
        return length / speed

    def should_reroute(
        self,
        vehicle_state: Dict[str, Any],
        traffic_metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        return False


class AdaptiveRoutingStrategy(RoutingStrategy):
    """
    PSO-adaptive routing strategy.

    Combines current travel time, exponential queue delay, predicted congestion penalties,
    stop count penalties, and historical congestion decay into edge weights. Dynamic rerouting
    is enabled when predicted congestion exceeds threshold or vehicle is stuck.
    """

    def __init__(
        self,
        adaptive_routing_threshold: float = 0.6,
        max_reroute_attempts: int = 3,
        min_reroute_interval: int = 60,
        params: Optional[List[float]] = None
    ):
        self.adaptive_routing_threshold = adaptive_routing_threshold
        self.max_reroute_attempts = max_reroute_attempts
        self.min_reroute_interval = min_reroute_interval
        # params: [travel_time_weight, queue_delay_weight, congestion_penalty_weight, hist_congestion_weight]
        self.params = params or [1.0, 1.0, 1.0, 1.0]

    def compute_edge_weight(
        self,
        u: str,
        v: str,
        edge_data: Dict[str, Any],
        traffic_metrics: Optional[Dict[str, Any]] = None
    ) -> float:
        travel_time_weight, queue_delay_weight, congestion_penalty_weight, hist_congestion_weight = self.params

        edge_length = float(edge_data.get('length', 1.0))
        speed = float(edge_data.get('speed', 13.89))
        nominal_travel_time = edge_length / max(0.1, speed)

        # Extract metrics if available
        metrics = traffic_metrics or {}
        if not isinstance(metrics, dict):
            # Extract from TrafficMetrics dataclass object if passed
            metrics = {
                'predicted_congestion': getattr(metrics, 'predicted_congestion', 0.0),
                'avg_speed': getattr(metrics, 'avg_speed', 0.0),
                'congestion_index': getattr(metrics, 'congestion_index', 0.0),
                'queue_length': getattr(metrics, 'queue_length', 0.0),
                'stop_count': getattr(metrics, 'stop_count', 0.0),
                'hist_congestion': getattr(metrics, 'hist_congestion', 0.0),
            }

        predicted_congestion = float(metrics.get('predicted_congestion', 0.0))
        avg_speed = float(metrics.get('avg_speed', 0.0))
        congestion_index = float(metrics.get('congestion_index', 0.0))
        queue_length = float(metrics.get('queue_length', 0.0))
        stop_count = float(metrics.get('stop_count', 0.0))
        hist_congestion = float(metrics.get('hist_congestion', 0.0))

        # Heavily penalize edges with predicted congestion
        congestion_multiplier = 5.0 if predicted_congestion > self.adaptive_routing_threshold else 1.0

        # Travel time calculation with speed prediction
        if avg_speed > 0:
            current_travel_time = edge_length / avg_speed
        else:
            current_travel_time = nominal_travel_time * (1.0 + congestion_index)

        # Queue delay estimation with exponential penalty
        queue_delay = queue_length * 3.0 * queue_delay_weight * (1.2 ** queue_length)

        # Congestion penalty using predicted congestion
        congestion_penalty = (predicted_congestion ** 2.0) * edge_length * congestion_penalty_weight

        # Historical congestion factor
        hist_factor = 1.0 + (hist_congestion * hist_congestion_weight * 0.5)

        # Combined edge weight
        edge_weight = (
            current_travel_time * travel_time_weight +
            queue_delay +
            congestion_penalty +
            stop_count * 3.0
        ) * hist_factor * congestion_multiplier

        return max(0.1, float(edge_weight))

    def should_reroute(
        self,
        vehicle_state: Dict[str, Any],
        traffic_metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        reroute_attempts = vehicle_state.get('reroute_attempts', 0)
        current_time = vehicle_state.get('current_time', 0.0)
        last_reroute_time = vehicle_state.get('last_reroute_time', 0.0) or 0.0

        if reroute_attempts >= self.max_reroute_attempts:
            return False

        if current_time - last_reroute_time <= self.min_reroute_interval:
            return False

        # Check if stuck
        speed = vehicle_state.get('speed', 10.0)
        waiting_time = vehicle_state.get('waiting_time', 0.0)
        if speed is not None and waiting_time is not None:
            if speed < 0.1 and waiting_time > 30:
                return True

        # Check upcoming route for predicted congestion
        upcoming_route = vehicle_state.get('upcoming_route', [])
        metrics_dict = traffic_metrics or {}
        for edge in upcoming_route:
            m = metrics_dict.get(edge, {})
            pred_cong = float(m.get('predicted_congestion', 0.0)) if isinstance(m, dict) else getattr(m, 'predicted_congestion', 0.0)
            if pred_cong > self.adaptive_routing_threshold:
                return True

        return False
