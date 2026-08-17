import os
import logging
from typing import Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
import traci

from .scenario_loader import load_scenario, ScenarioConfig
from .traffic_manager import AdvancedTrafficManager

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

scenario_config: Optional[ScenarioConfig] = None
traffic_manager: Optional[AdvancedTrafficManager] = None


from pathlib import Path
from typing import Optional, Union, Any

def init_traffic_manager(
    scenario_name: str = 'default',
    seed: Optional[int] = None,
    headless: bool = False,
    output_dir: Optional[Union[str, Path]] = None,
    run_id: Optional[str] = None,
    signal_strategy: Optional[Union[Any, str]] = None,
    routing_strategy: Optional[Union[Any, str]] = None
) -> AdvancedTrafficManager:
    """Initialize or reconfigure the traffic manager with specified scenario, seed, and headless options."""
    global traffic_manager, scenario_config
    scenario_config = load_scenario(scenario_name)
    traffic_manager = AdvancedTrafficManager(
        scenario_config=scenario_config,
        seed=seed,
        headless=headless,
        output_dir=output_dir,
        run_id=run_id,
        signal_strategy=signal_strategy,
        routing_strategy=routing_strategy
    )
    return traffic_manager


def get_traffic_manager() -> AdvancedTrafficManager:
    """Get or lazily initialize the global traffic manager instance."""
    global traffic_manager
    if traffic_manager is None:
        init_traffic_manager(os.getenv('SCENARIO_NAME', 'default'))
    return traffic_manager


@app.route('/process', methods=['POST'])
def process():
    """Add a new vehicle route without starting simulation."""
    try:
        data = request.get_json()
        initial_location = data.get('initial_location')
        destination = data.get('destination')
        
        logger.info(f"Received route data - From: {initial_location} To: {destination}")
        
        tm = get_traffic_manager()
        # Add vehicle to route file
        result = tm.add_vehicle_to_simulation(
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
        tm = get_traffic_manager()
        result = tm.start_simulation()
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
        tm = get_traffic_manager()
        # Read all updates from the file
        latest_updates = []
        if os.path.exists(tm.updates_file):
            with open(tm.updates_file, 'r') as f:
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
            vehicle_state = tm.vehicle_states.get(vehicle_id)
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
