# NexRoute Core Logic Testing Gaps

This document transparently lists core scientific and simulation components that remain un-tested or partially tested due to direct coupling with live SUMO TraCI C-level API sessions, and outlines recommendations for future decoupling refactors.

---

## 📌 Identified Testing Gaps

### 1. `AdvancedTrafficManager._update_vehicle_states()` ([`traffic_manager.py:L415`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/app/traffic_manager.py#L415))
- **Description**: Collects vehicle positions, speeds, accelerations, waiting times, and priorities across active simulation steps.
- **Testing Gap Rationale**: Hard-coupled to live TraCI simulation calls (`traci.vehicle.getIDList()`, `traci.vehicle.getSpeed()`, `traci.vehicle.getWaitingTime()`, `traci.vehicle.getLanePosition()`).
- **Remediation Plan**: Introduce a `VehicleStateProvider` interface abstracting TraCI queries behind a data repository interface, enabling full in-memory state injection without active SUMO sessions.

### 2. `AdvancedTrafficManager._apply_signal_optimization()` ([`traffic_manager.py:L600`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/app/traffic_manager.py#L600))
- **Description**: Applies particle swarm optimization outcomes to signal timing plans at intersections.
- **Testing Gap Rationale**: Calls `traci.trafficlight.setCompleteRedYellowGreenDefinition()` to update SUMO signal program logic directly.
- **Remediation Plan**: Abstract signal state mutations into a `SignalControlAdapter` layer.

### 3. `AdvancedTrafficManager._apply_vsl_optimization()` ([`traffic_manager.py:L760`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/app/traffic_manager.py#L760))
- **Description**: Dynamically updates edge speed limits based on congestion predictions.
- **Testing Gap Rationale**: Directly invokes `traci.edge.setMaxSpeed()` during active simulation runs.
- **Remediation Plan**: Abstract speed limit adjustments into a `SpeedLimitAdapter` layer.

---

## ✅ Core Logic Fully Tested

The following core mathematical engines are now 100% unit-tested in isolation:
1. **Particle Swarm Optimizer Core** ([`backend/tests/test_optimizer_core.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/tests/test_optimizer_core.py)): Analytical sphere function convergence, boundary constraint enforcement, and hand-computed single-step velocity/position arithmetic.
2. **Congestion Prediction Formula** ([`backend/tests/test_congestion_prediction.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/tests/test_congestion_prediction.py)): Linear factor weight sum invariant check ($\sum w_i = 1.00$) and output clamping bounds ($[0.10, 0.95]$).
3. **HCM Edge Metrics Computation** ([`backend/tests/test_edge_metrics.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/tests/test_edge_metrics.py)): PCU-weighted volume, HCM density, flow rate, occupancy percentage, and congestion index.
