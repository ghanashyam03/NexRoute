# Scenario Configuration Schema

NexRoute uses a YAML-based scenario configuration system to allow running simulations across different network topographies, demand profiles, and parameter settings without modifying python source code.

## File Location
Scenarios are located in `backend/scenarios/<scenario_name>/scenario.yaml`.

## Schema Definition

```yaml
name: <str>                  # Scenario identifier (e.g., "default")

sumo:                        # SUMO simulation files & options
  gui: <bool>                # Whether to launch SUMO with GUI (default: true)
  config_file: <str>         # Relative path to .sumocfg file
  net_file: <str>            # Relative path to .net.xml file
  route_file: <str>          # Relative path to .rou.xml file

# Optional Overrides for System Constants (defaults from app/config.py)
optimization_interval: <int>
congestion_thresholds:
  free_flow: <float>
  moderate: <float>
  heavy: <float>
  severe: <float>
  gridlock: <float>

speed_limits:
  urban: <float>
  arterial: <float>
  highway: <float>
  residential: <float>
  bus_lane: <float>

pcu_values:
  passenger: <float>
  truck: <float>
  trailer: <float>
  bus: <float>
  motorcycle: <float>
  bicycle: <float>

priority_weights:
  bus: <float>
  truck: <float>
  passenger: <float>
  motorcycle: <float>
  bicycle: <float>

max_reroute_attempts: <int>
min_reroute_interval: <int>
congestion_history_size: <int>
adaptive_routing_threshold: <float>

min_green_time: <int>
max_green_time: <int>
yellow_time: <int>
all_red_time: <int>

pso_particles: <int>
pso_iterations: <int>
```

> **Important**: All file paths under `sumo` must be relative to the directory containing the `scenario.yaml` file. `scenario_loader` will automatically resolve them into absolute paths at runtime.
