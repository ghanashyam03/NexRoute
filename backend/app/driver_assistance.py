import math
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

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
                    turn_msg = (f"Prepare to turn {turn['type']} in {turn['distance']:.0f}m ")
                    
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
