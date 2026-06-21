from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set, Any

@dataclass 
class VehicleState: 
    id: str 
    type: str 
    position: Tuple[float, float] 
    speed: float 
    route: List[str] 
    current_edge: str 
    destination: str 
    reroute_attempts: int 
    priority: float 
    last_reroute_time: float 
    waiting_time: float 
    lane_position: float 
    acceleration: float 
    last_speed: float = 0.0  # Added to track speed changes 
    last_position: Tuple[float, float] = (0.0, 0.0)  # Added to track position changes 
 
class TrafficMetrics: 
    def __init__(self): 
        self.volume: float = 0.0 
        self.speed_variance: float = 0.0 
        self.speed_entropy: float = 0.0 
        self.density: float = 0.0 
        self.avg_speed: float = 0.0 
        self.congestion_index: float = 0.0 
        self.queue_length: int = 0 
        self.flow_rate: float = 0.0 
        self.occupancy: float = 0.0 
        self.stop_count: int = 0  # Added to track number of stops 
        self.acceleration_variance: float = 0.0  # Added to track acceleration changes 
        self.predicted_congestion: float = 0.0  # New field for predicted congestion
