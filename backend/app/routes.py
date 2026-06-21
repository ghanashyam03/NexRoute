import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import traci

from .traffic_manager import AdvancedTrafficManager

logger = logging.getLogger(__name__)

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
