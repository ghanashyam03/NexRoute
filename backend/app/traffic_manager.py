import os
import sys
import random
import math
import logging
import threading
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any
import numpy as np
import networkx as nx
from scipy.stats import entropy
import traci
import sumolib

from .scenario_loader import ScenarioConfig, load_scenario
from .models import VehicleState, TrafficMetrics
from .optimizer import ParticleSwarmOptimizer
from .driver_assistance import DriverAssistance

logger = logging.getLogger(__name__)

class AdvancedTrafficManager: 
    def __init__(self, scenario_config: Optional[ScenarioConfig] = None): 
        if scenario_config is None:
            scenario_config = load_scenario('default')

        self.scenario_config = scenario_config
        self.sumo_config = scenario_config.sumo_config

         
        # System parameters with scenario overrides already merged by scenario_loader
        self.OPTIMIZATION_INTERVAL = scenario_config.OPTIMIZATION_INTERVAL
        self.CONGESTION_THRESHOLDS = scenario_config.CONGESTION_THRESHOLDS
         
        # Speed limits with scenario-specific overrides
        self.SPEED_LIMITS = scenario_config.SPEED_LIMITS
         
        # PCU values with scenario-specific overrides
        self.PCU_VALUES = scenario_config.PCU_VALUES
         
        # Priority weights with scenario-specific overrides
        self.PRIORITY_WEIGHTS = scenario_config.PRIORITY_WEIGHTS
         
        # Traffic management parameters with scenario-specific overrides
        self.MAX_REROUTE_ATTEMPTS = scenario_config.MAX_REROUTE_ATTEMPTS
        self.MIN_REROUTE_INTERVAL = scenario_config.MIN_REROUTE_INTERVAL
        self.CONGESTION_HISTORY_SIZE = scenario_config.CONGESTION_HISTORY_SIZE
        self.ADAPTIVE_ROUTING_THRESHOLD = scenario_config.ADAPTIVE_ROUTING_THRESHOLD
         
        # Signal timing parameters with scenario-specific overrides
        self.MIN_GREEN_TIME = scenario_config.MIN_GREEN_TIME
        self.MAX_GREEN_TIME = scenario_config.MAX_GREEN_TIME
        self.YELLOW_TIME = scenario_config.YELLOW_TIME
        self.ALL_RED_TIME = scenario_config.ALL_RED_TIME
         
        # PSO parameters with scenario-specific overrides
        self.PSO_PARTICLES = scenario_config.PSO_PARTICLES
        self.PSO_ITERATIONS = scenario_config.PSO_ITERATIONS
         
        # Initialize data structures 
        self.network_graph = nx.DiGraph() 
        self.traffic_metrics = defaultdict(TrafficMetrics) 
        self.vehicle_states: Dict[str, VehicleState] = {} 
        self.edge_congestion_history: Dict[str, List[float]] = defaultdict(list) 
        self.emergency_routes: Set[str] = set() 
        self.signal_states: Dict[str, Dict] = {} 
         
        # Initialize PSO attributes
        self.signal_pso = None
        self.speed_control_pso = None
        self.route_pso = None

        # Initialize driver assistance without vehicle ID
        self.driver_assistance = DriverAssistance()

        # Initialize system 
        self._initialize_system() 

        # Add new attributes for route file management
        self.route_file = self.sumo_config['route_file']
        self.vehicle_counter = 0
        self.vehicle_updates = {}
