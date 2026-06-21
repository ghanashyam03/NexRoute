# NexRoute

NexRoute is a production-quality Traffic Optimization and Route Management system that integrates a Flutter frontend with a Python-based backend powered by SUMO (Simulation of Urban MObility) and Particle Swarm Optimization (PSO).

## Codebase Architecture

The project is split into two main directories:

*   **[`/frontend`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/frontend)**: A cross-platform Flutter application providing route inputs, map visualizations, driver assistance updates, and speeds monitoring.
*   **[`/backend`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend)**: A Flask server that decomposes traffic management duties into modular subsystems:
    *   `app/config.py`: Traffic rules, constants, and SUMO configurations.
    *   `app/models.py`: Data representations for `VehicleState` and `TrafficMetrics`.
    *   `app/optimizer.py`: The PSO algorithm representing particle and swarm states.
    *   `app/driver_assistance.py`: Generates realtime navigation alerts and recommendations.
    *   `app/traffic_manager.py`: Connects NetworkX algorithms and TraCI interface loops.
    *   `app/routes.py`: Registers Flask REST endpoints.

## Getting Started

### Prerequisites

*   Python 3.8+
*   Flutter SDK (stable channel)
*   SUMO (Simulation of Urban MObility) installed and added to your environment variables

### Running the Backend

1.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Install requirements:
    ```bash
    pip install -r requirements.txt
    ```
3.  Start the Flask server:
    ```bash
    python run.py
    ```

### Running the Frontend

1.  Navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```
2.  Install Flutter dependencies:
    ```bash
    flutter pub get
    ```
3.  Run the application:
    ```bash
    flutter run
    ```
