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

from .config import (
    OPTIMIZATION_INTERVAL, CONGESTION_THRESHOLDS, SPEED_LIMITS,
    PCU_VALUES, PRIORITY_WEIGHTS, MAX_REROUTE_ATTEMPTS, MIN_REROUTE_INTERVAL,
    CONGESTION_HISTORY_SIZE, ADAPTIVE_ROUTING_THRESHOLD, MIN_GREEN_TIME,
    MAX_GREEN_TIME, YELLOW_TIME, ALL_RED_TIME, PSO_PARTICLES, PSO_ITERATIONS
)
from .scenario_loader import ScenarioConfig, load_scenario
from .models import VehicleState, TrafficMetrics
from .optimizer import ParticleSwarmOptimizer
from .driver_assistance import DriverAssistance

logger = logging.getLogger(__name__)

class AdvancedTrafficManager: 
    def __init__(self, scenario_config: Optional[ScenarioConfig] = None): 
        if scenario_config is None:
            scenario_config = load_scenario("default")
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
        self.updates_file = "driver_updates.txt"
        Path(self.updates_file).write_text("")
        
        # Initialize network without starting SUMO
        self.net = sumolib.net.readNet(self.sumo_config['net_file'])
        self._build_network_graph()
        self.simulation_running = False
        self.simulation_thread = None
        self.traci_started = False
 
    def _initialize_system(self): 
        """Initialize system without starting SUMO.""" 
        try: 
            # Verify file existence 
            for key, path in self.sumo_config.items(): 
                if key != 'gui' and not os.path.exists(path): 
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
                base_capacity = min(2300, 2000 + 25 * speed_limit)
                capacity_adjustment = min(1.1, (lane_width - 3.0) * 0.15 + 1.0)
                theoretical_capacity = base_capacity * num_lanes * capacity_adjustment * 0.97
                 
                attrs = { 
                    'length': edge.getLength(), 
                    'speed_limit': speed_limit, 
                    'lanes': num_lanes, 
                    'lane_width': lane_width, 
                    'capacity': theoretical_capacity, 
                    'priority': edge.getPriority(), 
                    'type': edge.getFunction(), 
                    'grade': edge.getGrade() if hasattr(edge, 'getGrade') else 0.0, 
                    'curvature': self._calculate_edge_curvature(edge)
                } 
                self.network_graph.add_edge(from_node, to_node, edge_id=edge_id, **attrs) 
             
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
            p1, p2, p3 = shape[0], shape[len(shape)//2], shape[-1] 
            v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]]) 
            v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]]) 
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)) 
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0)) 
            return angle / np.pi 
        except Exception as e: 
            logger.warning(f"Failed to calculate edge curvature: {str(e)}") 
            return 0.0 
 
    def _initialize_traffic_signals(self): 
        """Initialize traffic signal states with improved timing plans.""" 
        try: 
            for tls_id in traci.trafficlight.getIDList(): 
                programs = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id) 
                self.signal_states[tls_id] = { 
                    'current_phase': 0, 'phase_duration': 0, 'last_change': 0,
                    'programs': programs, 'controlled_lanes': traci.trafficlight.getControlledLanes(tls_id),
                    'controlled_links': traci.trafficlight.getControlledLinks(tls_id),
                    'optimal_params': np.array([35.0, 1.2, 0.6])
                } 
            logger.info(f"Initialized {len(self.signal_states)} traffic signals") 
            if self.signal_states: self._initialize_signal_pso()
        except Exception as e: 
            logger.error(f"Traffic signal initialization failed: {str(e)}") 
            raise 
 
    def _initialize_signal_pso(self): 
        bounds = [(20.0, 70.0), (0.6, 3.5), (0.3, 2.5)]
        self.signal_pso = ParticleSwarmOptimizer(num_particles=self.PSO_PARTICLES, num_dimensions=3, bounds=bounds, objective_function=self._evaluate_signal_timing, w=0.8, c1=1.8, c2=1.8, max_iterations=self.PSO_ITERATIONS)
        logger.info("PSO for signal timing optimization initialized") 
 
    def _initialize_speed_control_pso(self):
        bounds = [(0.3, 1.0), (0.3, 1.0), (0.3, 1.0), (0.5, 0.8)]
        self.speed_control_pso = ParticleSwarmOptimizer(num_particles=self.PSO_PARTICLES, num_dimensions=4, bounds=bounds, objective_function=self._evaluate_speed_control, w=0.8, c1=1.8, c2=1.8, max_iterations=self.PSO_ITERATIONS)
        logger.info("PSO for speed control optimization initialized")
 
    def _initialize_route_pso(self):
        bounds = [(0.3, 1.0), (0.3, 1.0), (0.3, 1.0), (0.3, 1.0)]
        self.route_pso = ParticleSwarmOptimizer(num_particles=self.PSO_PARTICLES, num_dimensions=4, bounds=bounds, objective_function=self._evaluate_routing_strategy, w=0.8, c1=1.8, c2=1.8, max_iterations=self.PSO_ITERATIONS)
        logger.info("PSO for route optimization initialized")

    def _predict_congestion(self, edge_id: str) -> float:
        try:
            metrics = self.traffic_metrics[edge_id]
            history = self.edge_congestion_history[edge_id]
            edge = self.net.getEdge(edge_id)
            if not history: return metrics.congestion_index
            current_density = metrics.density if hasattr(metrics, 'density') else 0
            current_speed = metrics.avg_speed if hasattr(metrics, 'avg_speed') else edge.getSpeed()
            current_occupancy = metrics.occupancy if hasattr(metrics, 'occupancy') else 0
            current_queue = metrics.queue_length if hasattr(metrics, 'queue_length') else 0
            historical_trend = 0.0
            if len(history) >= 5:
                weights = [math.exp(-i * 0.5) for i in range(5)]
                historical_trend = sum(h * w for h, w in zip(history[-5:], weights)) / sum(weights)
            congestion_rate = (history[-1] - history[-3]) / 3 if len(history) >= 3 else 0.0
            max_density = 140
            density_factor = min(1.0, current_density / (max_density * len(edge.getLanes())))
            speed_ratio = current_speed / max(edge.getSpeed(), 0.1)
            speed_factor = 1 - min(1.0, speed_ratio)
            queue_capacity = len(edge.getLanes()) * 10
            queue_factor = min(1.0, current_queue / max(1, queue_capacity))
            occupancy_factor = min(1.0, current_occupancy / 100)
            prediction = (0.25 * metrics.congestion_index + 0.20 * historical_trend + 0.15 * density_factor + 0.15 * queue_factor + 0.10 * speed_factor + 0.10 * occupancy_factor + 0.05 * max(0, congestion_rate))
            try:
                downstream_edges = [conn.getTo().getID() for conn in edge.getOutgoing()]
                if downstream_edges:
                    vals = [self.traffic_metrics[e].congestion_index for e in downstream_edges if e in self.traffic_metrics]
                    if vals: prediction = 0.8 * prediction + 0.2 * np.mean(vals)
            except Exception: pass
            return min(0.95, max(0.1, prediction))
        except Exception as e:
            logger.warning(f"Congestion prediction failed for edge {edge_id}: {str(e)}")
            return 0.5
 
    def _update_vehicle_states(self): 
        """Update vehicle states with improved tracking.""" 
        try: 
            current_time = traci.simulation.getTime() 
            new_states = {} 
            for vehicle_id in traci.vehicle.getIDList(): 
                try: 
                    vehicle_type = traci.vehicle.getVehicleClass(vehicle_id) 
                    current_route = traci.vehicle.getRoute(vehicle_id) 
                    speed = traci.vehicle.getSpeed(vehicle_id) 
                    acceleration = traci.vehicle.getAcceleration(vehicle_id) 
                    lane_position = traci.vehicle.getLanePosition(vehicle_id) 
                    position = traci.vehicle.getPosition(vehicle_id) 
                    state = self.vehicle_states.get(vehicle_id, None) 
                    reroute_attempts = state.reroute_attempts if state else 0 
                    last_reroute_time = state.last_reroute_time if state else 0 
                    speed_change = abs(speed - (state.last_speed if state else speed)) 
                    position_change = np.sqrt((position[0] - (state.last_position[0] if state else position[0]))**2 + (position[1] - (state.last_position[1] if state else position[1]))**2)
                    new_states[vehicle_id] = VehicleState(id=vehicle_id, type=vehicle_type, position=position, speed=speed, route=current_route, current_edge=traci.vehicle.getRoadID(vehicle_id), destination=current_route[-1], reroute_attempts=reroute_attempts, priority=self.PRIORITY_WEIGHTS.get(vehicle_type, 1.0), waiting_time=traci.vehicle.getWaitingTime(vehicle_id), lane_position=lane_position, last_speed=speed, last_position=position, speed_change=speed_change, position_change=position_change, acceleration=acceleration, last_reroute_time=last_reroute_time)
                except Exception as e: logger.warning(f"Error updating vehicle {vehicle_id}: {str(e)}")
            self.vehicle_states = new_states
        except Exception as e: logger.error(f"Vehicle state update failed: {str(e)}")

    def _compute_edge_metrics(self):
        try:
            for edge_id in traci.edge.getIDList():
                if edge_id.startswith(':'): continue
                try:
                    vehicle_count = traci.edge.getLastStepVehicleNumber(edge_id)
                    mean_speed = traci.edge.getLastStepMeanSpeed(edge_id)
                    occupancy = traci.edge.getLastStepOccupancy(edge_id)
                    waiting_time = traci.edge.getWaitingTime(edge_id)
                    edge = self.net.getEdge(edge_id)
                    edge_length = edge.getLength()
                    num_lanes = len(edge.getLanes())
                    density = vehicle_count / (edge_length / 1000.0 * max(1, num_lanes)) if edge_length > 0 else 0
                    speed_limit = edge.getSpeed()
                    congestion_index = max(0.0, min(1.0, 1.0 - mean_speed / speed_limit)) if speed_limit > 0 else 0.0
                    queue_length = sum(traci.lane.getLastStepHaltingNumber(l.getID()) for l in edge.getLanes())
                    flow_rate = vehicle_count * 3600.0 / max(1.0, traci.simulation.getDeltaT())
                    metric = self.traffic_metrics[edge_id]
                    metric.vehicle_count = vehicle_count
                    metric.avg_speed = mean_speed
                    metric.occupancy = occupancy
                    metric.waiting_time = waiting_time
                    metric.density = density
                    metric.queue_length = queue_length
                    metric.flow_rate = flow_rate
                    metric.congestion_index = congestion_index
                    self.edge_congestion_history[edge_id].append(congestion_index)
                    if len(self.edge_congestion_history[edge_id]) > self.CONGESTION_HISTORY_SIZE: self.edge_congestion_history[edge_id].pop(0)
                except Exception as e: logger.warning(f"Error computing metrics for edge {edge_id}: {str(e)}")
        except Exception as e: logger.error(f"Edge metric computation failed: {str(e)}")

    def _evaluate_system_performance(self):
        try:
            total_waiting = sum(traci.vehicle.getWaitingTime(v) for v in traci.vehicle.getIDList())
            total_time_loss = sum(traci.vehicle.getTimeLoss(v) for v in traci.vehicle.getIDList())
            active = traci.vehicle.getIDCount()
            return {'total_waiting_time': total_waiting, 'total_time_loss': total_time_loss, 'active_vehicles': active}
        except Exception as e:
            logger.error(f"Performance evaluation failed: {str(e)}")
            return {}

    def run_simulation(self, steps=3600):
        try:
            logger.info(f"Starting simulation for {steps} steps")
            for step in range(steps):
                traci.simulationStep()
                current_time = traci.simulation.getTime()
                self._update_vehicle_states()
                self._compute_edge_metrics()
                if step % self.OPTIMIZATION_INTERVAL == 0:
                    logger.info(f"Performing optimization at step {step}, time {current_time}")
                    self._optimize_traffic_signals()
                    self._optimize_speed_limits()
                    self._optimize_routing()
                    self._evaluate_system_performance()
                if len(self.vehicle_states) == 0 and traci.simulation.getMinExpectedNumber() == 0:
                    logger.info("All vehicles have completed their routes. Ending simulation.")
                    break
            final_metrics = self._evaluate_system_performance()
            logger.info(f"Simulation completed. Final metrics: {final_metrics}")
        except Exception as e:
            logger.error(f"Simulation failed: {str(e)}")
            raise
        finally:
            try: traci.close(); logger.info("Simulation resources cleaned up")
            except: pass

    def _evaluate_signal_timing(self, params):
        try:
            base_green_time, demand_weight, queue_weight = params
            total_score = 0.0; total_signals = 0
            for tls_id in traci.trafficlight.getIDList():
                signal_score = 0.0
                controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
                if not controlled_lanes: continue
                total_signals += 1
                current_phase = traci.trafficlight.getPhase(tls_id)
                phase_metrics = defaultdict(lambda: {'queue_length':0,'waiting_time':0,'flow_rate':0,'stopped_vehicles':0,'throughput':0,'delay':0})
                for lane_id in controlled_lanes:
                    try:
                        queue_length = traci.lane.getLastStepHaltingNumber(lane_id); waiting_time = traci.lane.getWaitingTime(lane_id); mean_speed = traci.lane.getLastStepMeanSpeed(lane_id); vehicle_count = traci.lane.getLastStepVehicleNumber(lane_id)
                        lane_vehicles = traci.lane.getLastStepVehicleIDs(lane_id); stopped_count = sum(1 for vid in lane_vehicles if traci.vehicle.getSpeed(vid) < 0.1); total_delay = sum(traci.vehicle.getAccumulatedWaitingTime(vid) for vid in lane_vehicles)
                        edge_id = lane_id.split('_')[0]; throughput = self.traffic_metrics[edge_id].flow_rate if edge_id in self.traffic_metrics else 0
                        phase_metrics[current_phase]['queue_length'] += queue_length; phase_metrics[current_phase]['waiting_time'] += waiting_time; phase_metrics[current_phase]['flow_rate'] += vehicle_count * mean_speed; phase_metrics[current_phase]['stopped_vehicles'] += stopped_count; phase_metrics[current_phase]['throughput'] += throughput; phase_metrics[current_phase]['delay'] += total_delay
                    except Exception as e: logger.warning(f"Error collecting metrics for lane {lane_id}: {str(e)}")
                for phase, metrics in phase_metrics.items():
                    norm_queue = metrics['queue_length'] / max(1, len(controlled_lanes)); norm_wait = metrics['waiting_time'] / max(1, metrics['flow_rate']); norm_stopped = metrics['stopped_vehicles'] / max(1, len(controlled_lanes)); norm_delay = metrics['delay'] / max(1, metrics['throughput'])
                    efficiency = (metrics['flow_rate'] / metrics['throughput']) * (1 - norm_queue) if metrics['throughput'] > 0 else 0
                    phase_score = norm_queue * queue_weight * 2.0 + norm_wait * demand_weight * 1.5 + norm_stopped * 1.2 + norm_delay * 1.3 + (1 - efficiency) * 1.5
                    signal_score += phase_score
                if len(traci.trafficlight.getIDList()) > 1:
                    for other_tls in traci.trafficlight.getIDList():
                        if other_tls != tls_id:
                            try:
                                distance = self._get_signal_distance(tls_id, other_tls)
                                if distance < 300:
                                    phase_diff = abs(current_phase - traci.trafficlight.getPhase(other_tls)); signal_score += phase_diff * (1 - distance / 300) * 0.5
                            except: pass
                if base_green_time < self.MIN_GREEN_TIME * 1.2: signal_score *= 1.5
                elif base_green_time > self.MAX_GREEN_TIME * 0.8: signal_score *= 1.3
                total_score += signal_score
            final_score = total_score / max(1, total_signals); final_score *= random.uniform(0.98, 1.02)
            return final_score if final_score > 0 else float('inf')
        except Exception as e:
            logger.error(f"Signal timing evaluation failed: {str(e)}"); return float('inf')

    def _get_signal_distance(self, tls1_id: str, tls2_id: str) -> float:
        try:
            pos1 = traci.junction.getPosition(tls1_id); pos2 = traci.junction.getPosition(tls2_id)
            return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
        except: return float('inf')

    def _evaluate_speed_control(self, params):
        try:
            density_weight, queue_weight, gap_weight, min_speed_factor = params; score = 0.0
            for edge_id in traci.edge.getIDList():
                if edge_id.startswith(':'): continue
                try:
                    vehicle_count = traci.edge.getLastStepVehicleNumber(edge_id); mean_speed = traci.edge.getLastStepMeanSpeed(edge_id); occupancy = traci.edge.getLastStepOccupancy(edge_id); edge = self.net.getEdge(edge_id); speed_limit = edge.getSpeed(); queue_length = sum(traci.lane.getLastStepHaltingNumber(l.getID()) for l in edge.getLanes()); edge_length = edge.getLength(); density = vehicle_count / edge_length if edge_length > 0 else 0; density_score = density * density_weight if density >= 0 else 0; queue_score = queue_length * queue_weight if queue_length >= 0 else 0; speed_score = (1.0 - mean_speed / speed_limit) * gap_weight if speed_limit > 0 and mean_speed >= 0 else 0; edge_score = density_score + queue_score + speed_score + occupancy * 0.5; score += max(0, edge_score)
                except (ValueError, ZeroDivisionError, AttributeError) as e: logger.warning(f"Error processing edge {edge_id}: {str(e)}")
            return score if score > 0 else float('inf')
        except Exception as e: logger.error(f"Speed control evaluation failed: {str(e)}"); return float('inf')

    def _evaluate_routing_strategy(self, params):
        try:
            travel_time_weight, queue_delay_weight, congestion_penalty_weight, hist_congestion_weight = params; score = 0.0
            for vehicle_id in traci.vehicle.getIDList():
                try:
                    score += traci.vehicle.getWaitingTime(vehicle_id) + traci.vehicle.getTimeLoss(vehicle_id)
                except: continue
            return score if score > 0 else float('inf')
        except Exception as e: logger.error(f"Routing strategy evaluation failed: {str(e)}"); return float('inf')

    def _optimize_traffic_signals(self):
        try:
            if not self.signal_states: self._initialize_traffic_signals()
            if self.signal_pso:
                best_params, _ = self.signal_pso.optimize(self.PSO_ITERATIONS)
                for tls_id in self.signal_states:
                    self.signal_states[tls_id]['optimal_params'] = best_params.copy()
        except Exception as e: logger.error(f"Traffic signal optimization failed: {str(e)}")

    def _optimize_speed_limits(self):
        try:
            if self.speed_control_pso is None: self._initialize_speed_control_pso()
            best_params, _ = self.speed_control_pso.optimize(self.PSO_ITERATIONS)
            for edge_id in traci.edge.getIDList():
                if edge_id.startswith(':'): continue
                try:
                    congestion = self._predict_congestion(edge_id); speed_factor = max(best_params[3], 1.0 - (0.5 * congestion + 0.4 * 0 + 0.3 * 0 + 0.2 * 0)); edge = self.net.getEdge(edge_id); new_speed = edge.getSpeed() * speed_factor; traci.edge.setMaxSpeed(edge_id, new_speed)
                except Exception: continue
        except Exception as e: logger.error(f"Speed limit optimization failed: {str(e)}")

    def _optimize_routing(self):
        try:
            if self.route_pso is None: self._initialize_route_pso()
            best_params, _ = self.route_pso.optimize(self.PSO_ITERATIONS)
            for vehicle_id in traci.vehicle.getIDList():
                try:
                    route = traci.vehicle.getRoute(vehicle_id)
                    if not route: continue
                    if any(self._predict_congestion(e) > self.ADAPTIVE_ROUTING_THRESHOLD for e in route):
                        self._reroute_vehicle(vehicle_id, best_params)
                except Exception: continue
        except Exception as e: logger.error(f"Routing optimization failed: {str(e)}")

    def _reroute_vehicle(self, vehicle_id, params):
        try:
            current_edge = traci.vehicle.getRoadID(vehicle_id); destination = traci.vehicle.getRoute(vehicle_id)[-1]
            route = traci.simulation.findRoute(current_edge, destination).edges
            if route: traci.vehicle.setRoute(vehicle_id, route)
        except Exception as e: logger.warning(f"Rerouting failed for vehicle {vehicle_id}: {str(e)}")

    def start_simulation(self):
        try:
            sumo_binary = 'sumo-gui' if self.sumo_config.get('gui', True) else 'sumo'
            sumo_cmd = [sumo_binary, '-c', self.sumo_config['config_file']]
            traci.start(sumo_cmd); self.traci_started = True; self._initialize_traffic_signals(); return {'status':'success','message':'Simulation started'}
        except Exception as e: logger.error(f"Simulation start failed: {str(e)}"); raise

    def add_vehicle_to_simulation(self, from_edge: str, to_edge: str):
        try:
            vehicle_id = f"vehicle_{self.vehicle_counter}"; self.vehicle_counter += 1
            route = nx.shortest_path(self.network_graph, self.net.getEdge(from_edge).getFromNode().getID(), self.net.getEdge(to_edge).getToNode().getID(), weight='length')
            edge_route = [self.network_graph[u][v]['edge_id'] for u,v in zip(route[:-1], route[1:])]
            if not edge_route: edge_route = [from_edge, to_edge]
            return {'vehicle_id':vehicle_id,'route_length':len(edge_route),'route':edge_route}
        except Exception as e: logger.error(f"Failed to add vehicle: {str(e)}"); raise
