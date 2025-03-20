import os 
import traci 
import sumolib 
import numpy as np 
import networkx as nx 
from scipy.stats import entropy 
from datetime import datetime 
import logging 
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass 
from collections import defaultdict 
import sys 
import itertools 
import random 
import math 
import json
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
from queue import Queue

# Configure logging with more detailed formatting 
logging.basicConfig( 
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s', 
    handlers=[ 
        logging.FileHandler('traffic_management.log'), 
        logging.StreamHandler() 
    ] 
) 
logger = logging.getLogger(__name__) 
 
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
 
@dataclass 
class Particle: 
    position: np.ndarray 
    velocity: np.ndarray 
    best_position: np.ndarray 
    best_score: float 
    current_score: float 
     
    def update_velocity(self, global_best_position: np.ndarray, w: float, c1: float, c2: float): 
        """Update particle velocity using PSO formula with improved convergence.""" 
        r1, r2 = random.random(), random.random() 
        cognitive_component = c1 * r1 * (self.best_position - self.position) 
        social_component = c2 * r2 * (global_best_position - self.position) 
        self.velocity = w * self.velocity + cognitive_component + social_component 
         
    def update_position(self, bounds: List[Tuple[float, float]]): 
        """Update particle position with improved bounds handling.""" 
        self.position = self.position + self.velocity 
        # Enforce bounds with smooth clamping 
        for i, (lower, upper) in enumerate(bounds): 
            if self.position[i] < lower: 
                self.position[i] = lower + abs(self.velocity[i]) * 0.1 
            elif self.position[i] > upper: 
                self.position[i] = upper - abs(self.velocity[i]) * 0.1 
 
class ParticleSwarmOptimizer: 
    def __init__(self,  
                 num_particles: int,  
                 num_dimensions: int,  
                 bounds: List[Tuple[float, float]],  
                 objective_function, 
                 w: float = 0.7, 
                 c1: float = 1.5, 
                 c2: float = 1.5, 
                 max_iterations: int = 50): 
         
        self.num_particles = num_particles 
        self.num_dimensions = num_dimensions 
        self.bounds = bounds 
        self.objective_function = objective_function 
        self.w = w 
        self.c1 = c1 
        self.c2 = c2 
        self.max_iterations = max_iterations 
         
        # Initialize particles 
        self.particles = [] 
        self.global_best_position = None 
        self.global_best_score = float('inf') 
        self.initialize_swarm() 
         
    def initialize_swarm(self): 
        """Initialize particle swarm with improved distribution.""" 
        for _ in range(self.num_particles): 
            # Random position within bounds with better distribution 
            position = np.array([ 
                random.uniform(low, high) for low, high in self.bounds 
            ]) 
             
            # Initialize velocity with magnitude based on bounds 
            velocity = np.array([ 
                random.uniform(-abs(high-low)*0.1, abs(high-low)*0.1)  
                for low, high in self.bounds 
            ]) 
             
            particle = Particle( 
                position=position.copy(), 
                velocity=velocity, 
                best_position=position.copy(), 
                best_score=float('inf'), 
                current_score=float('inf') 
            ) 
             
            # Evaluate initial position 
            score = self.objective_function(position) 
            particle.current_score = score 
            particle.best_score = score 
             
            if score < self.global_best_score: 
                self.global_best_score = score 
                self.global_best_position = position.copy() 
             
            self.particles.append(particle) 
     
    def optimize(self, iterations=None): 
        """Run PSO optimization with improved convergence.""" 
        if iterations is None: 
            iterations = self.max_iterations 
             
        for _ in range(iterations): 
            # Update each particle 
            for particle in self.particles: 
                # Update velocity and position 
                particle.update_velocity(self.global_best_position, self.w, self.c1, self.c2) 
                particle.update_position(self.bounds) 
                 
                # Evaluate new position 
                score = self.objective_function(particle.position) 
                particle.current_score = score 
                 
                # Update personal best with improved convergence 
                if score < particle.best_score: 
                    particle.best_score = score 
                    particle.best_position = particle.position.copy() 
                     
                    # Update global best with improved convergence 
                    if score < self.global_best_score: 
                        self.global_best_score = score 
                        self.global_best_position = particle.position.copy() 
             
            # Adaptive inertia weight 
            self.w *= 0.99 
         
        return self.global_best_position, self.global_best_score 
     
    def get_current_best(self): 
        """Return current best particle with improved accuracy.""" 
        return self.global_best_position, self.global_best_score 
     
    def optimize_step(self): 
        """Perform a single iteration of PSO with improved convergence.""" 
        for particle in self.particles: 
            particle.update_velocity(self.global_best_position, self.w, self.c1, self.c2) 
            particle.update_position(self.bounds) 
             
            score = self.objective_function(particle.position) 
            particle.current_score = score 
             
            if score < particle.best_score: 
                particle.best_score = score 
                particle.best_position = particle.position.copy() 
                 
                if score < self.global_best_score: 
                    self.global_best_score = score 
                    self.global_best_position = particle.position.copy() 
         
        # Adaptive inertia weight 
        self.w *= 0.99 
         
        return self.global_best_position, self.global_best_score 
 
class DriverAssistance:
    def __init__(self, vehicle_id=None):  # Change default from "115" to None
        self.vehicle_id = vehicle_id
        self.last_edge = None
        self.last_speed_advice = None
        self.last_route_advice = None
        self.last_maintain_advice = None
        self.updates_file = "driver_updates.txt"
        self.min_speed_diff = 2.0
        self.congestion_threshold = 0.65
        self.look_ahead_distance = 100  # meters to look ahead for predictions
        self.turn_warning_distance = 50  # meters before turn to warn
        self.speed_change_distance = 30  # meters before needed speed change
        self.direction_validation_threshold = 25  # degrees threshold for turn detection
        self.last_turn_warning = None
        
        # Create or clear the updates file
        Path(self.updates_file).write_text("")
        
    def _calculate_angle(self, edge1, edge2):
        """Calculate accurate angle between edges using full geometry."""
        try:
            # Get complete edge shapes
            shape1 = edge1.getShape()
            shape2 = edge2.getShape()
            
            if len(shape1) < 2 or len(shape2) < 2:
                return 0
            
            # Use last two points of first edge
            v1_x = shape1[-1][0] - shape1[-2][0]
            v1_y = shape1[-1][1] - shape1[-2][1]
            
            # Use first two points of second edge
            v2_x = shape2[1][0] - shape2[0][0]
            v2_y = shape2[1][1] - shape2[0][1]
            
            # Calculate angle using dot product and cross product
            dot_product = v1_x * v2_x + v1_y * v2_y
            cross_product = v1_x * v2_y - v1_y * v2_x
            
            angle = math.atan2(cross_product, dot_product)
            return math.degrees(angle)
            
        except Exception as e:
            logger.warning(f"Error calculating angle: {str(e)}")
            return 0

    def _validate_turn_direction(self, edge1, edge2):
        """Validate turn direction using multiple reference points."""
        try:
            angle = self._calculate_angle(edge1, edge2)
            
            # Double-check with alternative points if available
            shape1 = edge1.getShape()
            shape2 = edge2.getShape()
            
            if len(shape1) >= 3 and len(shape2) >= 3:
                # Calculate alternative angle using different points
                alt_angle = math.degrees(math.atan2(
                    shape2[2][1] - shape1[-3][1],
                    shape2[2][0] - shape1[-3][0]
                ))
                
                # If angles are significantly different, use more conservative estimate
                if abs(angle - alt_angle) > 30:
                    angle = (angle + alt_angle) / 2
            
            return angle
            
        except Exception as e:
            logger.warning(f"Error validating turn direction: {str(e)}")
            return 0

    def _get_turn_type(self, edge1, edge2):
        """Get accurate turn type with validation."""
        try:
            # Get and validate angle
            angle = self._validate_turn_direction(edge1, edge2)
            
            # Verify connection exists
            if not edge1.getConnections(edge2):
                logger.warning(f"No connection between edges {edge1.getID()} and {edge2.getID()}")
                return "straight"
            
            # Define turn types with conservative thresholds
            if abs(angle) < self.direction_validation_threshold:
                return "straight"
            elif angle >= 150:
                return "sharp left"  # Corrected from right to left
            elif angle <= -150:
                return "sharp right"  # Corrected from left to right
            elif angle >= 60:
                return "left"  # Corrected from right to left
            elif angle <= -60:
                return "right"  # Corrected from left to right
            elif angle > 0:
                return "slight left"  # Corrected from right to left
            else:
                return "slight right"  # Corrected from left to right
                
        except Exception as e:
            logger.warning(f"Error determining turn type: {str(e)}")
            return "straight"

    def _verify_route_connection(self, edge1_id, edge2_id):
        """Verify that two edges are actually connected."""
        try:
            edge1 = self.net.getEdge(edge1_id)
            edge2 = self.net.getEdge(edge2_id)
            
            # Get all outgoing connections from edge1
            connections = edge1.getOutgoing()
            
            # Check if edge2 is in the outgoing connections
            return edge2 in connections
            
        except Exception as e:
            logger.warning(f"Error verifying route connection: {str(e)}")
            return False

    def _get_upcoming_turns(self, current_edge_id, route, position):
        """Get validated upcoming turns."""
        try:
            current_index = route.index(current_edge_id)
            upcoming_turns = []
            cumulative_distance = 0
            current_edge = self.net.getEdge(current_edge_id)
            distance_on_edge = current_edge.getLength() - position
            
            # Look at next few edges
            for i in range(current_index, min(current_index + 4, len(route) - 1)):
                edge1_id = route[i]
                edge2_id = route[i + 1]
                
                # Verify connection exists
                if not self._verify_route_connection(edge1_id, edge2_id):
                    continue
                
                edge1 = self.net.getEdge(edge1_id)
                edge2 = self.net.getEdge(edge2_id)
                
                if i == current_index:
                    cumulative_distance = distance_on_edge
                else:
                    cumulative_distance += edge1.getLength()
                
                if cumulative_distance > self.look_ahead_distance:
                    break
                
                turn_type = self._get_turn_type(edge1, edge2)
                
                # Only include non-straight turns that have been validated
                if turn_type != "straight":
                    # Double check the turn direction
                    angle = self._validate_turn_direction(edge1, edge2)
                    if abs(angle) >= self.direction_validation_threshold:
                        upcoming_turns.append({
                            'distance': cumulative_distance,
                            'type': turn_type,
                            'edge_id': edge2_id,
                            'angle': angle  # Store angle for debugging
                        })
            
            return upcoming_turns
            
        except Exception as e:
            logger.warning(f"Error predicting turns: {str(e)}")
            return []

    def _predict_speed_changes(self, current_edge_id, route, traffic_metrics, current_speed):
        """Predict needed speed changes based on upcoming road conditions."""
        try:
            current_index = route.index(current_edge_id)
            speed_changes = []
            cumulative_distance = 0
            
            for i in range(current_index, min(current_index + 3, len(route) - 1)):
                edge_id = route[i]
                edge = self.net.getEdge(edge_id)
                
                if i == current_index:
                    cumulative_distance = edge.getLength() - current_speed
                else:
                    cumulative_distance += edge.getLength()
                
                if edge_id in traffic_metrics:
                    metrics = traffic_metrics[edge_id]
                    optimal_speed = self._calculate_optimal_speed(edge, metrics, current_speed)
                    
                    if optimal_speed is not None and abs(optimal_speed - current_speed) >= self.min_speed_diff:
                        speed_changes.append({
                            'distance': cumulative_distance,
                            'target_speed': optimal_speed,
                            'reason': self._get_speed_change_reason(metrics, edge)
                        })
            
            return speed_changes
            
        except Exception as e:
            logger.warning(f"Error predicting speed changes: {str(e)}")
            return []

    def _get_speed_change_reason(self, metrics, edge):
        """Get the reason for speed change."""
        if metrics.congestion_index > 0.8:
            return "heavy traffic ahead"
        elif metrics.queue_length > 3:
            return "queue ahead"
        elif metrics.predicted_congestion > 0.7:
            return "expected congestion"
        elif edge.getSpeed() < edge.getSpeed():
            return "speed limit change"
        return "traffic flow"

    def update_driver(self, net, vehicle_states, traffic_metrics):
        """Generate validated driver updates."""
        try:
            if self.vehicle_id not in vehicle_states:
                return
            
            self.net = net
            state = vehicle_states[self.vehicle_id]
            current_edge_id = state.current_edge
            
            if current_edge_id.startswith(':'):
                return
            
            updates = []
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Get and validate upcoming turns
            upcoming_turns = self._get_upcoming_turns(
                current_edge_id, 
                state.route, 
                state.lane_position
            )
            
            # Process validated turn warnings
            for turn in upcoming_turns:
                if turn['distance'] <= self.turn_warning_distance:
                    turn_msg = (f"Prepare to turn {turn['type']} in {turn['distance']:.0f}m "
                              f"(angle: {abs(turn['angle']):.1f}°)")
                    print(turn_msg)
                    print(self.vehicle_id)
                    
                    # Avoid duplicate warnings and validate turn type
                    if (turn_msg != self.last_turn_warning and 
                        abs(turn['angle']) >= self.direction_validation_threshold):
                        updates.append(turn_msg)
                        self.last_turn_warning = turn_msg
            
            # Process speed changes
            speed_changes = self._predict_speed_changes(
                current_edge_id,
                state.route,
                traffic_metrics,
                state.speed
            )
            
            # Check if speed should be maintained
            if not speed_changes and state.speed > 0:
                maintain_msg = f"Maintain current speed of {state.speed:.1f} m/s"
                print(maintain_msg)
                if maintain_msg != self.last_maintain_advice:
                    updates.append(maintain_msg)
                    self.last_maintain_advice = maintain_msg
            
            # Write valid updates
            if updates:
                with open(self.updates_file, "a") as f:
                    f.write(f"\n[{current_time}] Updates:\n")
                    for update in updates:
                        f.write(f"- {update}\n")
            
        except Exception as e:
            logger.error(f"Error updating driver assistance: {str(e)}")

    def _calculate_optimal_speed(self, edge, metrics, current_speed):
        """Calculate optimal speed based on conditions."""
        try:
            speed_limit = edge.getSpeed()
            
            # Factor in multiple conditions
            if metrics.congestion_index > 0.8:
                return min(speed_limit, max(5.0, current_speed * 0.7))
            elif metrics.queue_length > 3:
                return min(speed_limit, max(8.0, current_speed * 0.8))
            elif metrics.predicted_congestion > 0.7:
                return min(speed_limit, max(10.0, current_speed * 0.9))
            elif metrics.avg_speed > speed_limit * 0.9:
                return speed_limit
            
            # If conditions are good, maintain current speed if it's reasonable
            if current_speed <= speed_limit and current_speed >= speed_limit * 0.8:
                return current_speed
                
            return None
            
        except Exception as e:
            logger.warning(f"Error calculating optimal speed: {str(e)}")
            return None

class AdvancedTrafficManager: 
    def __init__(self): 
        self.sumo_config = { 
            'gui': True, 
            'config_file': r'C:\Users\ghana\OneDrive\Desktop\hell\edit.sumocfg', 
            'net_file': r'C:\Users\ghana\OneDrive\Desktop\hell\edit.net.xml', 
            'route_file': r'C:\Users\ghana\OneDrive\Desktop\hell\edit.rou.xml', 
        } 
         
        # System parameters with improved thresholds 
        self.OPTIMIZATION_INTERVAL = 30  # Reduced to 30 seconds for more frequent updates 
        self.CONGESTION_THRESHOLDS = { 
            'free_flow': 0.15,    
            'moderate': 0.35,    
            'heavy': 0.65,         
            'severe': 0.8,        
            'gridlock': 0.9        # Reduced from 0.95 
        } 
         
        # Speed limits with improved values 
        self.SPEED_LIMITS = { 
            'urban': 14.0,         # Increased from 13.89 
            'arterial': 17.0,      # Increased from 16.67 
            'highway': 28.0,       # Increased from 27.78 
            'residential': 8.5,    # Increased from 8.33 
            'bus_lane': 14.0       # Increased from 13.89 
        } 
         
        # PCU values with improved accuracy 
        self.PCU_VALUES = { 
            'passenger': 1.0, 
            'truck': 2.3,          # Reduced from 2.5 
            'trailer': 3.2,        # Reduced from 3.5 
            'bus': 2.2,            # Increased from 2.0 
            'motorcycle': 0.4,     # Reduced from 0.5 
            'bicycle': 0.2 
        } 
         
        # Priority weights with improved balance 
        self.PRIORITY_WEIGHTS = { 
            'bus': 3.5,            # Increased from 3.0 
            'truck': 2.2,          # Increased from 2.0 
            'passenger': 1.0, 
            'motorcycle': 0.8,     # Reduced from 1.0 
            'bicycle': 0.8         # Increased from 1.0 
        } 
         
        # Traffic management parameters with improved values 
        self.MAX_REROUTE_ATTEMPTS = 4  # Increased from 3 
        self.MIN_REROUTE_INTERVAL = 180  # Reduced from 300 
        self.CONGESTION_HISTORY_SIZE = 40  # Increased from 30 
        self.ADAPTIVE_ROUTING_THRESHOLD = 0.65  # Reduced from 0.7 
         
        # Signal timing parameters with improved values 
        self.MIN_GREEN_TIME = 20   # Increased from 15 
        self.MAX_GREEN_TIME = 100  # Increased from 90 
        self.YELLOW_TIME = 4       # Increased from 3 
        self.ALL_RED_TIME = 3      # Increased from 2 
         
        # PSO parameters with improved values 
        self.PSO_PARTICLES = 15    # Increased from 10 
        self.PSO_ITERATIONS = 7    # Increased from 5 
         
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
        self.updates_file = "driver_updates.txt"
        Path(self.updates_file).write_text("")
        
        # Initialize network without starting SUMO
        self.net = sumolib.net.readNet(self.sumo_config['net_file'])
        self._build_network_graph()  # Build NetworkX graph at initialization
        self.simulation_running = False
        self.simulation_thread = None
        self.traci_started = False  # New flag to track if TraCI has been started
 
    def _initialize_system(self): 
        """Initialize system without starting SUMO.""" 
        try: 
            # Verify file existence 
            for key, path in self.sumo_config.items(): 
                if not os.path.exists(path): 
                    raise FileNotFoundError(f"Required file not found: {path}") 
             
            # Only build network graph, don't start SUMO yet
            self.net = sumolib.net.readNet(self.sumo_config['net_file'])
            self._build_network_graph() 
            
            logger.info("Traffic Management System initialized successfully") 
             
        except Exception as e: 
            logger.error(f"System initialization failed: {str(e)}") 
            raise 
 
    def _build_network_graph(self): 
        """Build NetworkX graph with improved edge attributes.""" 
        try: 
            for edge in self.net.getEdges(): 
                edge_id = edge.getID() 
                from_node = edge.getFromNode().getID() 
                to_node = edge.getToNode().getID() 
                 
                # Calculate edge capacity with improved HCM formula 
                num_lanes = len(edge.getLanes()) 
                lane_width = edge.getLanes()[0].getWidth() 
                speed_limit = edge.getSpeed() 
                 
                # Improved HCM-based capacity calculation 
                base_capacity = min(2300, 2000 + 25 * speed_limit)  # Increased base capacity 
                capacity_adjustment = min(1.1, (lane_width - 3.0) * 0.15 + 1.0)  # Increased adjustment 
                 
                theoretical_capacity = ( 
                    base_capacity *  
                    num_lanes *  
                    capacity_adjustment *  
                    0.97  # Increased peak hour factor 
                ) 
                 
                attrs = { 
                    'length': edge.getLength(), 
                    'speed_limit': speed_limit, 
                    'lanes': num_lanes, 
                    'lane_width': lane_width, 
                    'capacity': theoretical_capacity, 
                    'priority': edge.getPriority(), 
                    'type': edge.getFunction(), 
                    'grade': edge.getGrade() if hasattr(edge, 'getGrade') else 0.0, 
                    'curvature': self._calculate_edge_curvature(edge)  # Added curvature 
                } 
                 
                self.network_graph.add_edge(from_node, to_node,  
                                         edge_id=edge_id, **attrs) 
             
            logger.info(f"Network graph built with {self.network_graph.number_of_nodes()} nodes and {self.network_graph.number_of_edges()} edges") 
             
        except Exception as e: 
            logger.error(f"Network graph building failed: {str(e)}") 
            raise 
     
    def _calculate_edge_curvature(self, edge): 
        """Calculate edge curvature for improved routing.""" 
        try: 
            shape = edge.getShape() 
            if len(shape) < 3: 
                return 0.0 
             
            # Calculate curvature using three points 
            p1, p2, p3 = shape[0], shape[len(shape)//2], shape[-1] 
             
            # Calculate vectors 
            v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]]) 
            v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]]) 
             
            # Calculate angle between vectors 
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)) 
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0)) 
             
            return angle / np.pi  # Normalize to [0,1] 
             
        except Exception as e: 
            logger.warning(f"Failed to calculate edge curvature: {str(e)}") 
            return 0.0 
 
    def _initialize_traffic_signals(self): 
        """Initialize traffic signal states with improved timing plans.""" 
        try: 
            for tls_id in traci.trafficlight.getIDList(): 
                # Get signal programs 
                programs = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id) 
                 
                # Store initial signal state with improved parameters 
                self.signal_states[tls_id] = { 
                    'current_phase': 0, 
                    'phase_duration': 0, 
                    'last_change': 0, 
                    'programs': programs, 
                    'controlled_lanes': traci.trafficlight.getControlledLanes(tls_id), 
                    'controlled_links': traci.trafficlight.getControlledLinks(tls_id), 
                    'optimal_params': np.array([35.0, 1.2, 0.6])  # Improved initial parameters 
                } 
                 
            logger.info(f"Initialized {len(self.signal_states)} traffic signals") 
             
            # Initialize PSO for signal timing 
            if self.signal_states: 
                self._initialize_signal_pso() 
             
        except Exception as e: 
            logger.error(f"Traffic signal initialization failed: {str(e)}") 
            raise 
 
    def _initialize_signal_pso(self): 
        """Initialize PSO for signal timing with improved parameters.""" 
        bounds = [ 
            (20.0, 70.0),  # Base green time (seconds) 
            (0.6, 3.5),    # Demand weight 
            (0.3, 2.5)     # Queue weight 
        ] 
         
        self.signal_pso = ParticleSwarmOptimizer( 
            num_particles=self.PSO_PARTICLES, 
            num_dimensions=3, 
            bounds=bounds, 
            objective_function=self._evaluate_signal_timing, 
            w=0.8,  # Increased inertia 
            c1=1.8,  # Increased cognitive parameter 
            c2=1.8,  # Increased social parameter 
            max_iterations=self.PSO_ITERATIONS 
        ) 
         
        logger.info("PSO for signal timing optimization initialized") 
 
    def _initialize_speed_control_pso(self):
        """Initialize PSO for speed control optimization."""
        bounds = [
            (0.3, 1.0),   # Density weight
            (0.3, 1.0),   # Queue weight
            (0.3, 1.0),   # Gap weight
            (0.5, 0.8)    # Minimum speed factor
        ]
        
        self.speed_control_pso = ParticleSwarmOptimizer(
            num_particles=self.PSO_PARTICLES,
            num_dimensions=4,
            bounds=bounds,
            objective_function=self._evaluate_speed_control,
            w=0.8,
            c1=1.8,
            c2=1.8,
            max_iterations=self.PSO_ITERATIONS
        )
        
        logger.info("PSO for speed control optimization initialized")

    def _initialize_route_pso(self):
        """Initialize PSO for route optimization."""
        bounds = [
            (0.3, 1.0),   # Travel time weight
            (0.3, 1.0),   # Queue delay weight
            (0.3, 1.0),   # Congestion penalty weight
            (0.3, 1.0)    # Historical congestion weight
        ]
        
        self.route_pso = ParticleSwarmOptimizer(
            num_particles=self.PSO_PARTICLES,
            num_dimensions=4,
            bounds=bounds,
            objective_function=self._evaluate_routing_strategy,
            w=0.8,
            c1=1.8,
            c2=1.8,
            max_iterations=self.PSO_ITERATIONS
        )
        
        logger.info("PSO for route optimization initialized")

    def _predict_congestion(self, edge_id: str) -> float:
        """Predict future congestion using historical data, current metrics, and traffic patterns."""
        try:
            metrics = self.traffic_metrics[edge_id]
            history = self.edge_congestion_history[edge_id]
            edge = self.net.getEdge(edge_id)
            
            if not history:
                return metrics.congestion_index

            # Get current metrics with safety checks
            current_density = metrics.density if hasattr(metrics, 'density') else 0
            current_speed = metrics.avg_speed if hasattr(metrics, 'avg_speed') else edge.getSpeed()
            current_occupancy = metrics.occupancy if hasattr(metrics, 'occupancy') else 0
            current_queue = metrics.queue_length if hasattr(metrics, 'queue_length') else 0
            
            # Calculate historical trend using exponential moving average
            alpha = 0.3  # Weight for recent values
            historical_trend = 0.0
            if len(history) >= 5:
                weights = [math.exp(-i * 0.5) for i in range(5)]  # Exponential decay weights
                weight_sum = sum(weights)
                historical_trend = sum(h * w for h, w in zip(history[-5:], weights)) / weight_sum

            # Calculate rate of change in congestion
            congestion_rate = 0.0
            if len(history) >= 3:
                congestion_rate = (history[-1] - history[-3]) / 3

            # Calculate normalized metrics
            max_density = 140  # vehicles per km per lane
            density_factor = min(1.0, current_density / (max_density * len(edge.getLanes())))
            
            speed_ratio = current_speed / max(edge.getSpeed(), 0.1)
            speed_factor = 1 - min(1.0, speed_ratio)
            
            queue_capacity = len(edge.getLanes()) * 10  # Assume 10 vehicles per lane as max queue
            queue_factor = min(1.0, current_queue / max(1, queue_capacity))
            
            occupancy_factor = min(1.0, current_occupancy / 100)

            # Time-based factors (peak hours consideration)
            current_time = traci.simulation.getTime()
            hour = (current_time / 3600) % 24
            
            # Define peak hours (morning and evening rush hours)
            morning_peak = 1.3 if 7 <= hour <= 10 else 1.0
            evening_peak = 1.3 if 16 <= hour <= 19 else 1.0
            time_factor = max(morning_peak, evening_peak)

            # Weighted combination of all factors
            prediction = (
                0.25 * metrics.congestion_index +     # Current congestion (highest weight)
                0.20 * historical_trend +             # Historical pattern
                0.15 * density_factor +               # Current density impact
                0.15 * queue_factor +                 # Queue impact
                0.10 * speed_factor +                 # Speed impact
                0.10 * occupancy_factor +             # Current occupancy
                0.05 * max(0, congestion_rate)        # Rate of change (trend)
            )

            # Apply time factor
            prediction *= time_factor

            # Apply downstream congestion influence
            try:
                downstream_edges = [conn.getTo().getID() for conn in edge.getOutgoing()]
                if downstream_edges:
                    downstream_congestion = np.mean([
                        self.traffic_metrics[e].congestion_index 
                        for e in downstream_edges 
                        if e in self.traffic_metrics
                    ])
                    # Blend with downstream congestion
                    prediction = 0.8 * prediction + 0.2 * downstream_congestion
            except:
                pass

            # Ensure prediction stays within bounds
            prediction = min(0.95, max(0.1, prediction))
            
            return prediction

        except Exception as e:
            logger.warning(f"Congestion prediction failed for edge {edge_id}: {str(e)}")
            return 0.5  # Return moderate congestion as fallback
 
    def _update_vehicle_states(self): 
        """Update vehicle states with improved tracking.""" 
        try: 
            current_time = traci.simulation.getTime() 
            new_states = {} 
             
            for vehicle_id in traci.vehicle.getIDList(): 
                try: 
                    vehicle_type = traci.vehicle.getVehicleClass(vehicle_id) 
                    current_route = traci.vehicle.getRoute(vehicle_id) 
                     
                    # Get detailed vehicle metrics 
                    speed = traci.vehicle.getSpeed(vehicle_id) 
                    acceleration = traci.vehicle.getAcceleration(vehicle_id) 
                    lane_position = traci.vehicle.getLanePosition(vehicle_id) 
                    position = traci.vehicle.getPosition(vehicle_id) 
                     
                    # Get or create vehicle state 
                    state = self.vehicle_states.get(vehicle_id, None) 
                    reroute_attempts = state.reroute_attempts if state else 0 
                    last_reroute_time = state.last_reroute_time if state else 0 
                     
                    # Calculate speed change 
                    speed_change = abs(speed - (state.last_speed if state else speed)) 
                     
                    # Calculate position change 
                    position_change = np.sqrt( 
                        (position[0] - (state.last_position[0] if state else position[0]))**2 + 
                        (position[1] - (state.last_position[1] if state else position[1]))**2 
                    ) 
                     
                    new_states[vehicle_id] = VehicleState( 
                        id=vehicle_id, 
                        type=vehicle_type, 
                        position=position, 
                        speed=speed, 
                        route=current_route, 
                        current_edge=traci.vehicle.getRoadID(vehicle_id), 
                        destination=current_route[-1], 
                        reroute_attempts=reroute_attempts, 
                        priority=self.PRIORITY_WEIGHTS.get(vehicle_type, 1.0), 
                        last_reroute_time=last_reroute_time, 
                        waiting_time=traci.vehicle.getWaitingTime(vehicle_id), 
                        lane_position=lane_position, 
                        acceleration=acceleration, 
                        last_speed=speed, 
                        last_position=position 
                    ) 
                     
                    # Log significant changes 
                    if state and ( 
                        speed_change > 3.0 or  # Reduced threshold 
                        abs(acceleration) > 1.5 or  # Reduced threshold 
                        position_change > 5.0  # Added position change check 
                    ): 
                        logger.debug(f"Vehicle {vehicle_id} state change - Speed: {speed:.2f}, Acc: {acceleration:.2f}, Pos: {position_change:.2f}") 
                     
                except traci.exceptions.TraCIException as e: 
                    logger.warning(f"Failed to update state for vehicle {vehicle_id}: {str(e)}") 
                    continue 
             
            self.vehicle_states = new_states 
            
            # Update driver assistance with traffic metrics
            self.driver_assistance.update_driver(self.net, self.vehicle_states, self.traffic_metrics)
            
        except Exception as e: 
            logger.error(f"Vehicle state update failed: {str(e)}") 
            raise 
 
    def _compute_edge_metrics(self) -> Dict[str, TrafficMetrics]: 
        """Compute edge metrics with improved calculations and congestion prediction.""" 
        try: 
            edge_metrics = defaultdict(TrafficMetrics) 
 
            # Collect raw data per edge 
            edge_data = defaultdict(lambda: { 
                'speeds': [], 
                'volumes': 0.0, 
                'queue': 0, 
                'occupancy': 0.0, 
                'stops': 0, 
                'accelerations': [] 
            }) 
 
            # First pass: collect raw data 
            for vehicle in self.vehicle_states.values(): 
                edge = vehicle.current_edge 
                if edge.startswith(':'):  
                    continue 
 
                # Calculate PCU-adjusted volume 
                pcu = self.PCU_VALUES.get(vehicle.type, 1.0) 
                edge_data[edge]['speeds'].append(vehicle.speed) 
                edge_data[edge]['volumes'] += pcu 
                edge_data[edge]['accelerations'].append(vehicle.acceleration) 
 
                # Count queued vehicles and stops 
                if vehicle.speed < 1.0: 
                    edge_data[edge]['queue'] += 1 
                if vehicle.speed < 0.1: 
                    edge_data[edge]['stops'] += 1 
 
            # Second pass: compute metrics for each edge 
            for edge in self.net.getEdges(): 
                edge_id = edge.getID() 
                data = edge_data[edge_id] 
                speeds = data['speeds'] 
                volume = data['volumes'] 
                accelerations = data['accelerations'] 
 
                metrics = TrafficMetrics() 
                metrics.volume = volume 
 
                if speeds: 
                    metrics.avg_speed = np.mean(speeds) 
                    metrics.speed_variance = np.var(speeds) if len(speeds) > 1 else 0 
                    metrics.speed_entropy = entropy(speeds) if len(speeds) > 1 else 0 
 
                if accelerations: 
                    metrics.acceleration_variance = np.var(accelerations) if len(accelerations) > 1 else 0 
 
                # Compute HCM-based metrics 
                edge_length = edge.getLength() 
                num_lanes = len(edge.getLanes()) 
 
                # Improved density calculation 
                metrics.density = (volume / (edge_length / 1000) / num_lanes) if edge_length > 0 else 0 
 
                # Improved flow rate calculation 
                metrics.flow_rate = volume * 3600  # Convert to vehicles/hour 
 
                # Queue length and stops 
                metrics.queue_length = data['queue'] 
                metrics.stop_count = data['stops'] 
 
                # Improved occupancy calculation 
                metrics.occupancy = min(100.0, (metrics.density / 130) * 100)  # Increased jam density 
 
                # Improved congestion index calculation 
                capacity = self.network_graph[edge.getFromNode().getID()][edge.getToNode().getID()]['capacity'] 
                metrics.congestion_index = min(1.0, metrics.flow_rate / capacity if capacity > 0 else 1.0) 

                # Predict future congestion
                metrics.predicted_congestion = self._predict_congestion(edge_id)
 
                # Update congestion history 
                self.edge_congestion_history[edge_id].append(metrics.congestion_index) 
                if len(self.edge_congestion_history[edge_id]) > self.CONGESTION_HISTORY_SIZE: 
                    self.edge_congestion_history[edge_id].pop(0) 
                 
                edge_metrics[edge_id] = metrics 
             
            # Update the system's traffic metrics 
            self.traffic_metrics = edge_metrics 
            return edge_metrics 
             
        except Exception as e: 
            logger.error(f"Edge metrics computation failed: {str(e)}") 
            raise 
 
    def _optimize_traffic_signals(self): 
        """Optimize traffic signals with improved proactive control."""
        try: 
            if self.signal_pso is None: 
                self._initialize_signal_pso() 
            
            # Check if there are any traffic signals
            tls_list = traci.trafficlight.getIDList()
            if not tls_list:
                logger.info("No traffic signals found in the network")
                return
            
            # Run PSO optimization with more iterations 
            best_params, best_score = self.signal_pso.optimize(5)  # Increased iterations 
            
            # Apply optimized parameters 
            self._apply_signal_optimization(best_params) 
            
            logger.info(f"Signal optimization completed with score: {best_score:.2f}") 
            
        except Exception as e: 
            logger.error(f"Traffic signal optimization failed: {str(e)}")
 
    def _apply_signal_optimization(self, params): 
        """Apply signal optimization with improved proactive control."""
        try: 
            base_green_time, demand_weight, queue_weight = params 
             
            for tls_id, signal_data in self.signal_states.items(): 
                try:
                    # Update optimal parameters 
                    signal_data['optimal_params'] = params 
                     
                    # Calculate adaptive timing for each signal 
                    controlled_lanes = signal_data['controlled_lanes'] 
                    
                    # Get current program logic
                    current_program = traci.trafficlight.getAllProgramLogics(tls_id)[0]  # Get first program
                    phase_count = len(current_program.phases)
                     
                    if phase_count == 0: 
                        continue 
                     
                    # Calculate phase durations with improved formula 
                    new_phases = [] 
                     
                    for i, phase in enumerate(current_program.phases): 
                        state = phase.state 
                         
                        total_demand = 0.0 
                        total_queue = 0.0 
                        total_stops = 0.0 
                        max_predicted_congestion = 0.0
                         
                        for j, lane_id in enumerate(controlled_lanes): 
                            if j < len(state) and state[j] in ['g', 'G']: 
                                edge_id = lane_id.split('_')[0] 
                                 
                                if edge_id in self.traffic_metrics: 
                                    metrics = self.traffic_metrics[edge_id] 
                                    total_demand += metrics.flow_rate 
                                    total_queue += metrics.queue_length 
                                    total_stops += metrics.stop_count 
                                    max_predicted_congestion = max(max_predicted_congestion, metrics.predicted_congestion)
                         
                        # Improved duration calculation with predicted congestion
                        duration = ( 
                            base_green_time +  
                            (total_demand / 500) * demand_weight +  # Adjusted scaling 
                            total_queue * queue_weight * 2.5 +      # Increased queue weight 
                            total_stops * 2.0 +                     # Increased stop penalty
                            max_predicted_congestion * 20.0         # Added predicted congestion impact
                        ) 
                         
                        # Enforce min/max limits with improved bounds 
                        duration = max(self.MIN_GREEN_TIME, min(self.MAX_GREEN_TIME, duration))
                        
                        # Create new phase with optimized duration
                        new_phase = traci.trafficlight.Phase(
                            duration=duration,
                            state=state,
                            minDur=self.MIN_GREEN_TIME,
                            maxDur=self.MAX_GREEN_TIME
                        )
                        new_phases.append(new_phase)
                     
                    # Create new program with improved parameters 
                    new_program = traci.trafficlight.Logic( 
                        programID=current_program.programID,
                        type=current_program.type,
                        currentPhaseIndex=current_program.currentPhaseIndex,
                        phases=new_phases
                    ) 
                     
                    # Apply the new program 
                    traci.trafficlight.setProgramLogic(tls_id, new_program) 
                     
                    # Additional measures for high congestion
                    if max_predicted_congestion > self.CONGESTION_THRESHOLDS['heavy']:
                        # Increase yellow time for safety
                        yellow_phases = [phase for phase in new_phases if 'y' in phase.state]
                        for phase in yellow_phases:
                            phase.duration = min(self.YELLOW_TIME * 1.5, phase.duration)
                        
                        # Add all-red phase if not present
                        if not any('r' * len(controlled_lanes) == phase.state for phase in new_phases):
                            all_red_phase = traci.trafficlight.Phase(
                                duration=self.ALL_RED_TIME,
                                state='r' * len(controlled_lanes),
                                minDur=self.ALL_RED_TIME,
                                maxDur=self.ALL_RED_TIME * 1.5
                            )
                            new_phases.append(all_red_phase)
                            new_program.phases = new_phases
                            traci.trafficlight.setProgramLogic(tls_id, new_program)
                    
                    logger.debug(f"Applied optimized timing to signal {tls_id}: {[phase.duration for phase in new_phases]}")
                
                except Exception as e:
                    logger.warning(f"Failed to optimize signal {tls_id}: {str(e)}")
                    continue
                 
        except Exception as e: 
            logger.error(f"Failed to apply signal optimization: {str(e)}")
 
    def _optimize_speed_limits(self): 
        """Optimize speed limits with improved proactive control."""
        try: 
            # First check if simulation is running and there are vehicles
            if not self.simulation_running or not traci.vehicle.getIDList():
                logger.debug("Skipping speed optimization - simulation not running or no vehicles")
                return

            if self.speed_control_pso is None: 
                self._initialize_speed_control_pso() 
            
            # Identify edges that need optimization
            edges_to_optimize = []
            for edge_id in traci.edge.getIDList():
                if edge_id.startswith(':'):  # Skip internal edges
                    continue
                    
                try:
                    # Get actual metrics from TraCI with null checks
                    occupancy = traci.edge.getLastStepOccupancy(edge_id) or 0.0
                    mean_speed = traci.edge.getLastStepMeanSpeed(edge_id) or 0.0
                    
                    # Get speed limit from net file
                    edge = self.net.getEdge(edge_id)
                    if edge is None:
                        continue
                        
                    speed_limit = edge.getSpeed()
                    
                    # Check for congestion using actual metrics with safe comparison
                    if occupancy > 0.7 or (mean_speed > 0 and speed_limit and mean_speed < speed_limit * 0.5):
                        edges_to_optimize.append(edge_id)
                except Exception as e:
                    logger.warning(f"Failed to check edge {edge_id} for optimization: {str(e)}")
                    continue
            
            if not edges_to_optimize: 
                return 
            
            # Run PSO optimization with null check
            best_params = None
            best_score = float('inf')
            
            if self.speed_control_pso is not None:
                try:
                    best_params, best_score = self.speed_control_pso.optimize_step() 
                except Exception as e:
                    logger.warning(f"PSO optimization failed: {str(e)}")
                    return
            
            if best_params is None:
                logger.warning("Speed optimization failed to find valid parameters")
                return
            
            # Apply optimized parameters 
            self._apply_speed_optimization(edges_to_optimize, best_params) 
            
            logger.info(f"Speed optimization completed for {len(edges_to_optimize)} edges with score: {best_score:.2f}") 
            
        except Exception as e: 
            logger.error(f"Speed limit optimization failed: {str(e)}")
 
    def _apply_speed_optimization(self, edges_to_optimize, params): 
        """Apply speed optimization with improved proactive control."""
        try: 
            density_weight, queue_weight, gap_weight, min_speed_factor = params 
             
            for edge_id in edges_to_optimize: 
                try:
                    metrics = self.traffic_metrics.get(edge_id)
                    if metrics is None:
                        continue
                    
                    edge = self.net.getEdge(edge_id)
                    if edge is None:
                        continue
                        
                    normal_speed = edge.getSpeed()
                     
                    # Calculate speed adjustment factors with safety checks
                    congestion = metrics.predicted_congestion if metrics.predicted_congestion is not None else 0
                    queue_factor = min(1.0, metrics.queue_length / 5) * queue_weight if metrics.queue_length is not None else 0
                    density_factor = min(1.0, metrics.density / 60) * density_weight if metrics.density is not None else 0
                    stop_factor = min(1.0, metrics.stop_count / 3) * 0.4 if metrics.stop_count is not None else 0
                    
                    # Calculate speed adjustment with improved formula
                    speed_factor = max( 
                        min_speed_factor, 
                        1.0 - (
                            congestion * 0.5 +  # Increased impact
                            queue_factor * 0.4 +  # Increased impact
                            density_factor * 0.3 +  # Increased impact
                            stop_factor * 0.2  # Added impact
                        )
                    ) 
                     
                    # Apply new speed limit with improved bounds 
                    new_speed = normal_speed * speed_factor 
                    new_speed = max(3.0, min(new_speed, normal_speed))  # Increased minimum speed
                     
                    # Apply speed limit using TraCI
                    traci.edge.setMaxSpeed(edge_id, new_speed) 
                     
                    logger.debug(f"Applied speed limit to edge {edge_id}: {new_speed:.2f} m/s (factor: {speed_factor:.2f})") 
                     
                    # Harmonize speeds with improved safety
                    self._harmonize_speeds(edge_id, new_speed, gap_weight) 
                     
                    # Additional measures for congested edges
                    if metrics.predicted_congestion > self.CONGESTION_THRESHOLDS['heavy']:
                        # Increase minimum gap between vehicles
                        for vehicle in self.vehicle_states.values():
                            if vehicle.current_edge == edge_id:
                                try:
                                    traci.vehicle.setMinGap(vehicle.id, 2.0)  # Increased minimum gap
                                except traci.exceptions.TraCIException:
                                    continue
                    
                except Exception as e: 
                    logger.warning(f"Failed to apply speed limit to edge {edge_id}: {str(e)}") 
                    continue 
                     
        except Exception as e: 
            logger.error(f"Failed to apply speed optimization: {str(e)}")
 
    def _harmonize_speeds(self, edge_id, target_speed, gap_weight): 
        """Harmonize speeds with improved safety and flow."""
        try: 
            edge_vehicles = [v for v in self.vehicle_states.values() if v.current_edge == edge_id] 
             
            if len(edge_vehicles) < 2: 
                return 
                 
            edge_vehicles.sort(key=lambda v: v.lane_position) 
             
            for i, vehicle in enumerate(edge_vehicles): 
                # Base target speed with improved safety margin 
                v_target = target_speed * 0.95  # Increased safety margin
                 
                if i > 0: 
                    lead_vehicle = edge_vehicles[i-1] 
                    position_gap = lead_vehicle.lane_position - vehicle.lane_position 
                     
                    if position_gap > 0 and vehicle.speed > 0: 
                        time_gap = position_gap / vehicle.speed 
                         
                        # Improved gap-based speed adjustment 
                        if time_gap < 2.0:  # Reduced minimum gap
                            gap_factor = min(1.0, time_gap / 2.0)
                            v_target = min(v_target, lead_vehicle.speed * gap_factor) 
                        elif time_gap > 4.0:  # Reduced maximum gap
                            v_target = min(target_speed, lead_vehicle.speed * 1.1)  # Reduced speed increase
                 
                # Apply smooth speed adjustment with improved control
                try: 
                    current_speed = vehicle.speed 
                    # More aggressive speed adjustment
                    new_speed = current_speed + (v_target - current_speed) * gap_weight * 0.15
                    traci.vehicle.setSpeed(vehicle.id, new_speed) 
                except: 
                    continue 
                     
        except Exception as e: 
            logger.warning(f"Speed harmonization failed for edge {edge_id}: {str(e)}") 
 
    def _optimize_routing(self): 
        """Optimize routing with improved vehicle selection and proactive rerouting."""
        try: 
            # First check if simulation is running and there are vehicles
            if not self.simulation_running or not traci.vehicle.getIDList():
                logger.debug("Skipping route optimization - simulation not running or no vehicles")
                return

            if self.route_pso is None: 
                self._initialize_route_pso() 
             
            best_params = None
            best_score = float('inf')
            
            if self.route_pso is not None:
                try:
                    best_params, best_score = self.route_pso.optimize_step() 
                except Exception as e:
                    logger.warning(f"PSO optimization failed: {str(e)}")
                    return
            
            if best_params is None:
                logger.warning("Route optimization failed to find valid parameters")
                return
            
            current_time = traci.simulation.getTime() 
            candidates = set()  # Using set to avoid duplicates
            
            # First, identify edges with predicted congestion
            congested_edges = set()
            for edge_id, metrics in self.traffic_metrics.items():
                if metrics and metrics.predicted_congestion and metrics.predicted_congestion > self.ADAPTIVE_ROUTING_THRESHOLD:
                    congested_edges.add(edge_id)
                    logger.info(f"Edge {edge_id} predicted to be congested: {metrics.predicted_congestion:.2f}")
            
            # Then find vehicles that will pass through these edges
            for vehicle_id, state in self.vehicle_states.items():
                if not state or not state.current_edge or state.current_edge == state.destination:
                    continue
                
                try:
                    # Get vehicle's current route with null check
                    if not traci.vehicle.getIDList() or vehicle_id not in traci.vehicle.getIDList():
                        continue
                        
                    current_route = traci.vehicle.getRoute(vehicle_id)
                    if not current_route:
                        continue
                        
                    current_route_index = traci.vehicle.getRouteIndex(vehicle_id)
                    if current_route_index is None:
                        continue
                    
                    # Check upcoming edges in route
                    upcoming_route = current_route[current_route_index:]
                    
                    # If any upcoming edge is predicted to be congested, add vehicle to candidates
                    for edge in upcoming_route:
                        if edge in congested_edges:
                            if (state.reroute_attempts < self.MAX_REROUTE_ATTEMPTS and 
                                current_time - (state.last_reroute_time or 0) > self.MIN_REROUTE_INTERVAL):
                                candidates.add(vehicle_id)
                                logger.info(f"Vehicle {vehicle_id} will be rerouted proactively due to predicted congestion on {edge}")
                            break
                    
                    # Also check for currently stuck vehicles as a fallback
                    if state.speed is not None and state.waiting_time is not None:
                        if state.speed < 0.1 and state.waiting_time > 30:
                            candidates.add(vehicle_id)
                
                except traci.exceptions.TraCIException as e:
                    logger.warning(f"Failed to check route for vehicle {vehicle_id}: {str(e)}")
                    continue
            
            if candidates:
                self._apply_adaptive_routing(list(candidates), best_params)
                logger.info(f"Proactively rerouting {len(candidates)} vehicles")
             
        except Exception as e:
            logger.error(f"Routing optimization failed: {str(e)}")
 
    def _apply_adaptive_routing(self, candidate_vehicles, params): 
        """Apply adaptive routing with improved edge weights and alternative routes."""
        try: 
            travel_time_weight, queue_delay_weight, congestion_penalty_weight, hist_congestion_weight = params 
            current_time = traci.simulation.getTime() 
             
            # Calculate edge weights first to avoid recomputation
            edge_weights = {} 
            for edge in self.net.getEdges(): 
                edge_id = edge.getID() 
                edge_length = edge.getLength() 
                nominal_travel_time = edge_length / edge.getSpeed() 
                 
                metrics = self.traffic_metrics.get(edge_id, TrafficMetrics()) 
                 
                # Heavily penalize edges with predicted congestion
                congestion_multiplier = 5.0 if metrics.predicted_congestion > self.ADAPTIVE_ROUTING_THRESHOLD else 1.0
                
                # Improved travel time calculation with speed prediction
                if metrics.avg_speed > 0: 
                    current_travel_time = edge_length / metrics.avg_speed 
                else: 
                    current_travel_time = nominal_travel_time * (1 + metrics.congestion_index) 
                 
                # Enhanced queue delay estimation with exponential penalty
                queue_delay = metrics.queue_length * 3.0 * queue_delay_weight * (1.2 ** metrics.queue_length)
                 
                # Improved congestion penalty using predicted congestion
                congestion_penalty = (metrics.predicted_congestion ** 2.0) * edge_length * congestion_penalty_weight
                 
                # Historical congestion with improved decay 
                hist_congestion = np.mean(self.edge_congestion_history[edge_id][-5:]) if self.edge_congestion_history[edge_id] else 0 
                hist_factor = 1.0 + (hist_congestion * hist_congestion_weight * 0.5)
                 
                # Combined edge weight with improved balancing 
                edge_weight = ( 
                    current_travel_time * travel_time_weight + 
                    queue_delay + 
                    congestion_penalty + 
                    metrics.stop_count * 3.0  # Increased stop penalty
                ) * hist_factor * congestion_multiplier  # Apply congestion multiplier
                 
                edge_weights[edge_id] = max(0.1, edge_weight) 

            # Update edge travel times in SUMO
            for edge_id, weight in edge_weights.items():
                try:
                    traci.edge.adaptTraveltime(edge_id, weight)
                except traci.exceptions.TraCIException:
                    continue
             
            # Reroute vehicles with improved weights and alternative routes
            for vehicle_id in candidate_vehicles: 
                try: 
                    state = self.vehicle_states[vehicle_id] 
                    
                    # Get current route for validation
                    current_route = traci.vehicle.getRoute(vehicle_id)
                    current_index = traci.vehicle.getRouteIndex(vehicle_id)
                    current_edge = current_route[current_index]
                    
                    # Set routing mode to use aggregated travel times
                    traci.vehicle.setRoutingMode(vehicle_id, 1)  # 1 = routing mode with aggregated times
                    
                    # Calculate new route using Dijkstra's algorithm
                    try:
                        new_route = traci.simulation.findRoute(
                            current_edge,
                            state.destination,
                            routingMode=1  # Use aggregated times
                        ).edges
                        
                        if new_route and current_edge in new_route:
                            # Verify the new route is valid and different from current
                            if new_route != current_route[current_index:]:
                                traci.vehicle.setRoute(vehicle_id, new_route)
                                logger.info(f"Successfully rerouted vehicle {vehicle_id} with new route")
                                
                                state.reroute_attempts += 1 
                                state.last_reroute_time = current_time
                    except traci.exceptions.TraCIException as e:
                        logger.warning(f"Failed to find new route for vehicle {vehicle_id}: {str(e)}")
                        continue
                     
                except Exception as e: 
                    logger.warning(f"Failed to reroute vehicle {vehicle_id}: {str(e)}") 
                    continue 
                     
        except Exception as e: 
            logger.error(f"Adaptive routing application failed: {str(e)}")
 
    def _evaluate_system_performance(self): 
        """Evaluate system performance with improved metrics.""" 
        try: 
            global_metrics = { 
                'total_vehicles': len(self.vehicle_states), 
                'avg_speed': np.mean([v.speed for v in self.vehicle_states.values()]) if self.vehicle_states else 0, 
                'avg_waiting_time': np.mean([v.waiting_time for v in self.vehicle_states.values()]) if self.vehicle_states else 0, 
                'total_travel_time': traci.simulation.getTime() * len(self.vehicle_states), 
                'system_congestion': np.mean([m.congestion_index for m in self.traffic_metrics.values()]) if self.traffic_metrics else 0, 
                'total_distance': sum(traci.vehicle.getDistance(vid) for vid in traci.vehicle.getIDList()), 
                'completed_trips': traci.simulation.getArrivedNumber(), 
                'avg_trip_duration': np.mean([traci.vehicle.getTimeLoss(vid) for vid in traci.vehicle.getIDList()]) if traci.vehicle.getIDList() else 0, 
                'avg_acceleration': np.mean([v.acceleration for v in self.vehicle_states.values()]) if self.vehicle_states else 0, 
                'total_stops': sum(m.stop_count for m in self.traffic_metrics.values()), 
                'predicted_congestion': np.mean([m.predicted_congestion for m in self.traffic_metrics.values()]) if self.traffic_metrics else 0
            } 
             
            logger.info(f"System Performance: " 
                        f"Vehicles: {global_metrics['total_vehicles']}, " 
                        f"Avg Speed: {global_metrics['avg_speed']:.2f} m/s, " 
                        f"Congestion: {global_metrics['system_congestion']:.2f}, " 
                        f"Predicted Congestion: {global_metrics['predicted_congestion']:.2f}, " 
                        f"Completed Trips: {global_metrics['completed_trips']}, " 
                        f"Total Stops: {global_metrics['total_stops']}") 
             
            return global_metrics 
             
        except Exception as e: 
            logger.error(f"Performance evaluation failed: {str(e)}") 
            return {} 
 
    def run_simulation(self, steps=3600): 
        """Run simulation with improved performance monitoring.""" 
        try: 
            logger.info(f"Starting simulation for {steps} steps") 
             
            for step in range(steps): 
                traci.simulationStep() 
                current_time = traci.simulation.getTime() 
                 
                # Update states 
                self._update_vehicle_states() 
                self._compute_edge_metrics() 
                 
                # Periodic optimization 
                if step % self.OPTIMIZATION_INTERVAL == 0: 
                    logger.info(f"Performing optimization at step {step}, time {current_time}") 
                     
                    self._optimize_traffic_signals() 
                    self._optimize_speed_limits() 
                    self._optimize_routing() 
                     
                    metrics = self._evaluate_system_performance() 
                 
                # End simulation if all vehicles completed 
                if len(self.vehicle_states) == 0 and traci.simulation.getMinExpectedNumber() == 0: 
                    logger.info("All vehicles have completed their routes. Ending simulation.") 
                    break 
                     
            final_metrics = self._evaluate_system_performance() 
            logger.info(f"Simulation completed. Final metrics: {final_metrics}") 
             
        except Exception as e: 
            logger.error(f"Simulation failed: {str(e)}") 
            raise 
        finally: 
            try: 
                traci.close() 
                logger.info("Simulation resources cleaned up") 
            except: 
                pass 
 
    def _evaluate_signal_timing(self, params):
        """Evaluate signal timing parameters using comprehensive metrics."""
        try:
            base_green_time, demand_weight, queue_weight = params
            total_score = 0.0
            total_signals = 0
            
            for tls_id in traci.trafficlight.getIDList():
                signal_score = 0.0
                controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
                
                if not controlled_lanes:
                    continue
                    
                total_signals += 1
                current_phase = traci.trafficlight.getPhase(tls_id)
                phase_duration = traci.trafficlight.getPhaseDuration(tls_id)
                
                # Collect metrics for all controlled lanes
                lane_metrics = []
                for lane_id in controlled_lanes:
                    try:
                        # Queue metrics
                        queue_length = traci.lane.getLastStepHaltingNumber(lane_id)
                        waiting_time = traci.lane.getWaitingTime(lane_id)
                        
                        # Flow metrics
                        mean_speed = traci.lane.getLastStepMeanSpeed(lane_id)
                        vehicle_count = traci.lane.getLastStepVehicleNumber(lane_id)
                        occupancy = traci.lane.getLastStepOccupancy(lane_id)
                        
                        # Calculate lane capacity and utilization
                        lane = self.net.getLane(lane_id)
                        lane_length = lane.getLength()
                        max_speed = lane.getSpeed()
                        
                        # Calculate lane efficiency
                        speed_ratio = mean_speed / max_speed if max_speed > 0 else 0
                        flow_rate = vehicle_count * 3600 / phase_duration if phase_duration > 0 else 0
                        
                        lane_metrics.append({
                            'queue_length': queue_length,
                            'waiting_time': waiting_time,
                            'speed_ratio': speed_ratio,
                            'flow_rate': flow_rate,
                            'occupancy': occupancy,
                            'vehicle_count': vehicle_count
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error collecting metrics for lane {lane_id}: {str(e)}")
                        continue
                
                if not lane_metrics:
                    continue
                
                # Calculate signal-specific scores
                avg_queue = np.mean([m['queue_length'] for m in lane_metrics])
                max_queue = max(m['queue_length'] for m in lane_metrics)
                avg_wait = np.mean([m['waiting_time'] for m in lane_metrics])
                avg_speed_ratio = np.mean([m['speed_ratio'] for m in lane_metrics])
                total_flow = sum(m['flow_rate'] for m in lane_metrics)
                avg_occupancy = np.mean([m['occupancy'] for m in lane_metrics])
                
                # Queue penalty (higher weight for longer queues)
                queue_penalty = (avg_queue * 1.0 + max_queue * 0.5) * queue_weight
                
                # Waiting time penalty
                wait_penalty = avg_wait * demand_weight
                
                # Flow efficiency reward
                flow_reward = total_flow * 0.01 * avg_speed_ratio
                
                # Phase utilization penalty
                utilization_penalty = abs(0.7 - avg_occupancy) * 10  # Optimal occupancy around 70%
                
                # Combine metrics with improved weights
                signal_score = (
                    queue_penalty * 1.5 +      # Increased weight for queues
                    wait_penalty * 1.2 +       # Increased weight for waiting time
                    utilization_penalty * 0.8 - # Reduced weight for utilization
                    flow_reward                # Reward for good flow
                )
                
                # Add coordination penalty if applicable
                if len(traci.trafficlight.getIDList()) > 1:
                    # Check adjacent signals
                    for other_tls in traci.trafficlight.getIDList():
                        if other_tls != tls_id:
                            try:
                                distance = self._get_signal_distance(tls_id, other_tls)
                                if distance < 300:  # Only consider nearby signals
                                    phase_diff = abs(traci.trafficlight.getPhase(tls_id) - 
                                                   traci.trafficlight.getPhase(other_tls))
                                    signal_score += phase_diff * 2.0  # Penalty for poor coordination
                            except:
                                continue
                
                total_score += max(0, signal_score)  # Ensure non-negative score
            
            # Normalize score by number of signals
            final_score = total_score / max(1, total_signals)
            
            # Add penalty for extreme green times
            if base_green_time < self.MIN_GREEN_TIME + 5 or base_green_time > self.MAX_GREEN_TIME - 5:
                final_score *= 1.5  # Penalty for extreme timing
            
            return final_score if final_score > 0 else float('inf')
            
        except Exception as e:
            logger.error(f"Signal timing evaluation failed: {str(e)}")
            return float('inf')

    def _get_signal_distance(self, tls1_id: str, tls2_id: str) -> float:
        """Calculate distance between two traffic signals."""
        try:
            pos1 = traci.junction.getPosition(tls1_id)
            pos2 = traci.junction.getPosition(tls2_id)
            return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
        except:
            return float('inf')

    def _evaluate_speed_control(self, params):
        """Evaluate speed control parameters using actual TraCI metrics."""
        try:
            density_weight, queue_weight, gap_weight, min_speed_factor = params
            score = 0.0
            
            for edge_id in traci.edge.getIDList():
                if edge_id.startswith(':'):  # Skip internal edges
                    continue
                    
                try:
                    # Get actual edge metrics from TraCI using correct methods
                    vehicle_count = traci.edge.getLastStepVehicleNumber(edge_id)
                    mean_speed = traci.edge.getLastStepMeanSpeed(edge_id)
                    occupancy = traci.edge.getLastStepOccupancy(edge_id)
                    
                    # Get speed limit from net file instead of TraCI
                    edge = self.net.getEdge(edge_id)
                    speed_limit = edge.getSpeed()
                    
                    # Get queue length from lanes
                    queue_length = 0
                    lanes = edge.getLanes()
                    for lane in lanes:
                        lane_id = lane.getID()
                        queue_length += traci.lane.getLastStepHaltingNumber(lane_id)
                    
                    # Calculate density using actual edge length
                    edge_length = edge.getLength()
                    density = vehicle_count / edge_length if edge_length > 0 else 0
                    
                    # Calculate score components with safety checks
                    density_score = density * density_weight if density >= 0 else 0
                    queue_score = queue_length * queue_weight if queue_length >= 0 else 0
                    speed_score = (1.0 - (mean_speed / speed_limit)) * gap_weight if speed_limit > 0 and mean_speed >= 0 else 0
                    
                    # Combine metrics into score (lower is better)
                    edge_score = (
                        density_score +
                        queue_score +
                        speed_score +
                        occupancy * 0.5  # Additional occupancy penalty
                    )
                    
                    score += max(0, edge_score)  # Ensure non-negative score
                    
                except (ValueError, ZeroDivisionError, AttributeError) as e:
                    logger.warning(f"Error processing edge {edge_id}: {str(e)}")
                    continue
            
            return score if score > 0 else float('inf')
            
        except Exception as e:
            logger.error(f"Speed control evaluation failed: {str(e)}")
            return float('inf')

    def _evaluate_routing_strategy(self, params):
        """Evaluate routing strategy parameters using actual TraCI metrics."""
        try:
            travel_time_weight, queue_delay_weight, congestion_penalty_weight, hist_congestion_weight = params
            score = 0.0
            
            for vehicle_id in traci.vehicle.getIDList():
                try:
                    # Get actual vehicle metrics from TraCI
                    waiting_time = traci.vehicle.getWaitingTime(vehicle_id)
                    time_loss = traci.vehicle.getTimeLoss(vehicle_id)
                    speed = traci.vehicle.getSpeed(vehicle_id)
                    
                    # Get current edge metrics
                    current_edge = traci.vehicle.getRoadID(vehicle_id)
                    if current_edge and not current_edge.startswith(':'):
                        try:
                            edge = self.net.getEdge(current_edge)
                            edge_occupancy = traci.edge.getLastStepOccupancy(current_edge)
                            edge_queue = 0
                            
                            # Sum up queue lengths for all lanes
                            for lane in edge.getLanes():
                                lane_id = lane.getID()
                                edge_queue += traci.lane.getLastStepHaltingNumber(lane_id)
                            
                            speed_limit = edge.getSpeed()
                            
                            # Calculate score components with safety checks
                            waiting_score = waiting_time * queue_delay_weight if waiting_time >= 0 else 0
                            time_loss_score = time_loss * travel_time_weight if time_loss >= 0 else 0
                            congestion_score = edge_occupancy * congestion_penalty_weight if edge_occupancy >= 0 else 0
                            queue_score = edge_queue * 0.5 if edge_queue >= 0 else 0
                            
                            # Speed penalty for slow vehicles with safety check
                            speed_penalty = (1.0 - (speed / speed_limit)) * 0.3 if speed_limit > 0 and speed >= 0 else 0
                            
                            # Combine metrics into score (lower is better)
                            vehicle_score = (
                                waiting_score +
                                time_loss_score +
                                congestion_score +
                                queue_score +
                                speed_penalty
                            )
                            
                            score += max(0, vehicle_score)  # Ensure non-negative score
                            
                        except (ValueError, ZeroDivisionError, AttributeError) as e:
                            logger.warning(f"Error processing edge {current_edge} for vehicle {vehicle_id}: {str(e)}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Failed to evaluate vehicle {vehicle_id}: {str(e)}")
                    continue
            
            return score if score > 0 else float('inf')
            
        except Exception as e:
            logger.error(f"Routing strategy evaluation failed: {str(e)}")
            return float('inf')

    def calculate_shortest_route(self, from_edge: str, to_edge: str) -> List[str]:
        """Calculate shortest route between two edges using NetworkX and validate for SUMO."""
        try:
            # Verify edges exist and are valid for vehicles
            from_edge_obj = self.net.getEdge(from_edge)
            to_edge_obj = self.net.getEdge(to_edge)
            
            if not from_edge_obj or not to_edge_obj:
                raise ValueError(f"Invalid edge IDs: {from_edge} or {to_edge}")
                
            # Check if edges allow passenger vehicles
            if not self._is_edge_allowed(from_edge_obj) or not self._is_edge_allowed(to_edge_obj):
                raise ValueError(f"Edges {from_edge} or {to_edge} do not allow passenger vehicles")

            # Get nodes corresponding to edges
            from_node = from_edge_obj.getToNode().getID()
            to_node = to_edge_obj.getFromNode().getID()
            
            # Find shortest path using NetworkX with custom weight function
            try:
                path = nx.shortest_path(
                    self.network_graph, 
                    from_node, 
                    to_node, 
                    weight=lambda u, v, d: self._calculate_edge_weight(u, v, d)
                )
                
                # Convert node path to edge path and validate connections
                edges = []
                for i in range(len(path) - 1):
                    edge_data = self.network_graph[path[i]][path[i + 1]]
                    edge_id = edge_data['edge_id']
                    edge = self.net.getEdge(edge_id)
                    
                    # Skip if edge doesn't allow vehicles
                    if not self._is_edge_allowed(edge):
                        continue
                        
                    # Verify connection to next edge
                    if edges and not self._verify_edge_connection(edges[-1], edge_id):
                        raise ValueError(f"No valid connection between edges {edges[-1]} and {edge_id}")
                        
                    edges.append(edge_id)
                
                # Verify connection to final edge
                if edges and not self._verify_edge_connection(edges[-1], to_edge):
                    raise ValueError(f"No valid connection to destination edge {to_edge}")
                
                # Add final destination edge
                edges.append(to_edge)
                
                # Validate complete route using SUMO's route check
                if not self._validate_route(edges):
                    raise ValueError("Invalid route: edges are not properly connected")
                
                return edges
                
            except nx.NetworkXNoPath:
                raise ValueError(f"No route found between {from_edge} and {to_edge}")
                
        except Exception as e:
            logger.error(f"Route calculation failed: {str(e)}")
            raise

    def _is_edge_allowed(self, edge) -> bool:
        """Check if edge allows passenger vehicles."""
        try:
            # Check if edge allows passenger vehicles
            allowed = edge.allows("passenger")
            
            # Additional checks for edge validity
            if edge.getFunction() in ["internal", "connector"]:
                return False
                
            # Check if edge has lanes
            if len(edge.getLanes()) == 0:
                return False
                
            return allowed
        except Exception as e:
            logger.warning(f"Error checking edge permissions: {str(e)}")
            return False

    def _calculate_edge_weight(self, u, v, edge_data) -> float:
        """Calculate edge weight considering various factors."""
        try:
            edge_id = edge_data['edge_id']
            edge = self.net.getEdge(edge_id)
            
            if not self._is_edge_allowed(edge):
                return float('inf')
            
            # Base weight is edge length
            weight = edge_data['length']
            
            # Add penalties for various factors
            if edge.getSpeed() < 8.0:  # Slow edges
                weight *= 1.5
                
            if len(edge.getLanes()) == 1:  # Single-lane roads
                weight *= 1.2
                
            # Add congestion penalty if available
            if edge_id in self.traffic_metrics:
                metrics = self.traffic_metrics[edge_id]
                if metrics.congestion_index > 0.7:
                    weight *= (1 + metrics.congestion_index)
            
            return weight
            
        except Exception as e:
            logger.warning(f"Error calculating edge weight: {str(e)}")
            return float('inf')

    def _validate_route(self, edges: List[str]) -> bool:
        """Validate complete route using SUMO's route check."""
        try:
            # Check if route has at least start and end
            if len(edges) < 2:
                return False
                
            # Verify each pair of consecutive edges
            for i in range(len(edges) - 1):
                edge1 = self.net.getEdge(edges[i])
                edge2 = self.net.getEdge(edges[i + 1])
                
                # Check if edges are connected
                connections = edge1.getConnections(edge2)
                if not connections:
                    logger.warning(f"No connection between edges {edges[i]} and {edges[i + 1]}")
                    return False
                    
                # Verify connection allows passenger vehicles
                for conn in connections:
                    if conn.getFrom().allows("passenger") and conn.getTo().allows("passenger"):
                        break
                else:
                    logger.warning(f"No valid connection for passenger vehicles between {edges[i]} and {edges[i + 1]}")
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Route validation failed: {str(e)}")
            return False

    def _add_route_to_file(self, vehicle_id: str, edges: List[str]):
        """Add new route to the route file at the beginning."""
        try:
            from xml.etree import ElementTree as ET
            import random
            
            logger.info(f"Adding new route for vehicle {vehicle_id}")
            
            # Read existing route file
            tree = ET.parse(self.route_file)
            root = tree.getroot()
            
            # Check if vtypes are already defined
            vtype_exists = False
            for child in root:
                if child.tag == 'vType' and child.get('id') == 'passenger':
                    vtype_exists = True
                    break
            
            # Add vType definition if it doesn't exist
            if not vtype_exists:
                vtype_element = ET.Element("vType", {
                    "id": "passenger",
                    "accel": "2.6",
                    "decel": "4.5",
                    "sigma": "0.5",
                    "length": "5.0",
                    "minGap": "2.5",
                    "maxSpeed": "70.0",
                    "speedDev": "0.1",
                    "vClass": "passenger",
                    "guiShape": "passenger",
                    "color": "1,1,0"  # Yellow color for visibility
                })
                # Insert vType at the beginning of the file
                root.insert(0, vtype_element)
            
            # Generate random ID between 1 and 100000
            random_id = str(0)
            while any(vehicle.get('id') == random_id for vehicle in root.findall('vehicle')):
                random_id = str(random.randint(1000, 100000))
            
            logger.info(f"Generated random vehicle ID: {random_id}")
            
            # Create new route element
            route_element = ET.Element("route", {
                "edges": " ".join(edges),
                "color": "1,1,0"  # Match vehicle color
            })
            
            # Create vehicle element with improved attributes
            vehicle_element = ET.Element("vehicle", {
                "id": random_id,
                "type": "passenger",
                "depart": "1.00",
                "departSpeed": "max",
                "departLane": "best",
                "departPos": "base",  # Add departure position
                "arrivalPos": "max",  # Add arrival position
                "speedFactor": "1.0"  # Add speed factor
            })
            
            # Add route element as child of vehicle element
            vehicle_element.append(route_element)
            
            # Insert vehicle element at the beginning, after vType and any non-vehicle elements
            insert_index = 0
            for i, child in enumerate(root):
                if child.tag == 'vehicle':
                    insert_index = i
                    break
            root.insert(insert_index, vehicle_element)
            
            # Write back to file with proper formatting
            tree.write(self.route_file, encoding='utf-8', xml_declaration=True)
            
            logger.info(f"Successfully wrote vehicle {random_id} to route file with {len(edges)} edges")
            
            return random_id
            
        except Exception as e:
            logger.error(f"Failed to update route file: {str(e)}")
            raise

    def add_vehicle_to_simulation(self, from_edge: str, to_edge: str) -> Dict[str, Any]:
        try:
            # Verify edge connection before calculating route
            if not self._verify_edge_connection(from_edge, to_edge):
                raise ValueError(f"No valid connection between {from_edge} and {to_edge}")
            
            # Calculate route
            route = self.calculate_shortest_route(from_edge, to_edge)
            logger.info(f"Found route with {len(route)} edges: {' -> '.join(route)}")
            
            # Add route to route file and get random vehicle ID
            vehicle_id = self._add_route_to_file(None, route)
            logger.info(f"Successfully added vehicle {vehicle_id} to route file")
            
            # Update driver assistance with new vehicle ID
            self.driver_assistance = DriverAssistance(vehicle_id)
            
            # Initialize updates tracking for this vehicle
            self.vehicle_updates[vehicle_id] = []
            
            return {
                "status": "success",
                "vehicle_id": vehicle_id,
                "route_length": len(route),
                "route": route
            }
            
        except Exception as e:
            logger.error(f"Failed to add vehicle: {str(e)}")
            raise

    def _verify_edge_connection(self, from_edge: str, to_edge: str) -> bool:
        """Verify that there exists a valid path between two edges."""
        try:
            # Get nodes corresponding to edges
            from_node = self.net.getEdge(from_edge).getToNode().getID()
            to_node = self.net.getEdge(to_edge).getFromNode().getID()
            
            # Check if path exists using NetworkX
            return nx.has_path(self.network_graph, from_node, to_node)
        except Exception as e:
            logger.error(f"Error verifying edge connection: {str(e)}")
            return False

    def get_vehicle_updates(self, vehicle_id: str) -> Dict[str, Any]:
        """Get updates for a specific vehicle."""
        try:
            if vehicle_id not in self.vehicle_states:
                return {"status": "not_found"}
            
            state = self.vehicle_states[vehicle_id]
            return {
                "status": "active",
                "position": state.position,
                "speed": state.speed,
                "current_edge": state.current_edge,
                "waiting_time": state.waiting_time,
                "route_progress": traci.vehicle.getRouteIndex(vehicle_id) if self.simulation_running else 0
            }
            
        except traci.exceptions.TraCIException:
            return {"status": "completed"}
        except Exception as e:
            logger.error(f"Error getting vehicle updates: {str(e)}")
            return {"status": "error", "message": str(e)}

    def start_simulation(self):
        """Start SUMO simulation with GUI."""
        if self.simulation_running:
            return {"status": "error", "message": "Simulation already running"}
        
        try:
            if not self.traci_started:  # Only start TraCI if not already started
                # Initialize SUMO with GUI
                sumo_binary = sumolib.checkBinary('sumo-gui')
                sumo_cmd = [
                    sumo_binary,
                    '-c', self.sumo_config['config_file'],
                    '--net-file', self.sumo_config['net_file'],
                    '--route-files', self.sumo_config['route_file'],
                    '--time-to-teleport', '-1',
                    '--waiting-time-memory', '10000',
                    '--device.emissions.probability', '1.0',
                    '--device.rerouting.probability', '1.0',
                    '--device.rerouting.period', '20',
                    '--step-length', '1.0',
                    '--collision.action', 'warn',
                    '--lateral-resolution', '0.1',
                    '--no-step-log', 'true',
                    '--no-warnings', 'true',
                    '--start', 'false'  # Start paused
                ]
                
                # Start SUMO
                traci.start(sumo_cmd)
                self.traci_started = True
                
                # Initialize traffic signals
                self._initialize_traffic_signals()
            
            # Start simulation in a separate thread
            self.simulation_running = True
            self.simulation_thread = threading.Thread(target=self.run_simulation)
            self.simulation_thread.start()
            
            return {"status": "success", "message": "Simulation started successfully"}
            
        except Exception as e:
            logger.error(f"Failed to start simulation: {str(e)}")
            if 'already active' in str(e):
                try:
                    traci.close()
                    self.traci_started = False
                    return self.start_simulation()  # Retry after closing
                except:
                    pass
            return {"status": "error", "message": str(e)}

    def get_driver_updates(self, vehicle_id: str) -> List[str]:
        """Get the latest driver updates for a specific vehicle."""
        try:
            if not self.simulation_running:
                return []
                
            if vehicle_id not in self.vehicle_states:
                return []
                
            # Read the updates file
            if not os.path.exists(self.updates_file):
                return []
                
            updates = []
            current_updates = []
            with open(self.updates_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('['):  # New timestamp
                        if current_updates:
                            updates.append(current_updates)
                        current_updates = [line.strip()]
                    else:
                        current_updates.append(line.strip())
                        
            if current_updates:
                updates.append(current_updates)
                
            # Return the most recent update
            return updates[-1] if updates else []
            
        except Exception as e:
            logger.error(f"Error getting driver updates: {str(e)}")
            return []

# Create Flask app and traffic manager instance
app = Flask(__name__)
CORS(app)
traffic_manager = AdvancedTrafficManager()

@app.route('/process', methods=['POST'])
def process():
    """Add a new vehicle route without starting simulation."""
    try:
        data = request.get_json()
        initial_location = data.get('initial_location')
        destination = data.get('destination')
        
        logger.info(f"Received route data - From: {initial_location} To: {destination}")
        
        # Add vehicle to route file
        result = traffic_manager.add_vehicle_to_simulation(
            from_edge=initial_location,
            to_edge=destination
        )
        
        return jsonify({
            "status": "success",
            "message": "Vehicle route added successfully",
            "data": {
                "from": initial_location,
                "to": destination,
                "vehicle_id": result["vehicle_id"],
                "route_length": result["route_length"],
                "route": result["route"]
            }
        })
    except ValueError as ve:
        logger.error(f"Invalid route data: {ve}")
        return jsonify({
            "status": "error",
            "message": str(ve)
        }), 400
    except Exception as e:
        logger.error(f"Error processing route data: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/start', methods=['POST'])
def start_simulation():
    """Start the SUMO simulation with GUI."""
    try:
        result = traffic_manager.start_simulation()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to start simulation: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/updates/<vehicle_id>', methods=['GET'])
def get_updates(vehicle_id):
    """Get the latest updates for a specific vehicle."""
    try:
        # Read all updates from the file
        latest_updates = []
        if os.path.exists(traffic_manager.updates_file):
            with open(traffic_manager.updates_file, 'r') as f:
                lines = f.readlines()
                current_block = []
                for line in lines:
                    line = line.strip()
                    if line.startswith('['):  # New timestamp block
                        if current_block:
                            latest_updates.extend(current_block)
                        current_block = []
                    elif line.startswith('-'):
                        current_block.append(line[2:])  # Remove "- " prefix
                
                # Add the last block
                if current_block:
                    latest_updates.extend(current_block)

        # Check if vehicle has completed its journey by verifying it has reached its destination
        is_completed = False
        try:
            # Get vehicle's current state
            vehicle_state = traffic_manager.vehicle_states.get(vehicle_id)
            if vehicle_state:
                # Check if vehicle is still in simulation
                try:
                    current_edge = traci.vehicle.getRoadID(vehicle_id)
                    # Check if vehicle has reached its destination
                    is_completed = current_edge == vehicle_state.destination
                except traci.exceptions.TraCIException:
                    # If vehicle is not found in simulation, check if it reached destination
                    arrived_vehicles = traci.simulation.getArrivedIDList()
                    is_completed = vehicle_id in arrived_vehicles
            else:
                # If vehicle state is not found, check arrived vehicles
                arrived_vehicles = traci.simulation.getArrivedIDList()
                is_completed = vehicle_id in arrived_vehicles

            if is_completed and not any("Journey completed!" in update for update in latest_updates):
                latest_updates.append("Journey completed!")
        except Exception as e:
            logger.warning(f"Error checking vehicle completion: {str(e)}")
            is_completed = False

        return jsonify({
            "status": "success",
            "driver_updates": latest_updates,
            "vehicle_state": {
                "status": "completed" if is_completed else "active",
                "is_arrived": is_completed
            }
        })
    except Exception as e:
        logger.error(f"Failed to get updates: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/', methods=['GET'])
def root():
    return jsonify({"message": "Traffic Optimization API is running"})

if __name__ == "__main__":
    try:
        traffic_manager = AdvancedTrafficManager()
        
        app.run(debug=True)
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        import traceback
        logger.critical(traceback.format_exc())
        sys.exit(1)
