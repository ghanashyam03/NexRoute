# NexRoute Scenario Tools

This directory contains utility scripts for generating synthetic SUMO traffic simulation scenarios.

## Prerequisites

Generating scenarios requires a local installation of SUMO (Simulation of Urban MObility) and the `SUMO_HOME` environment variable set:

- **Windows**: `set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo` (or `$env:SUMO_HOME="C:\Program Files (x86)\Eclipse\Sumo"`)
- **Linux / macOS**: `export SUMO_HOME=/usr/share/sumo` (or `/usr/local/opt/sumo/share/sumo`)

---

## Grid Scenario Generator (`generate_grid_scenario.py`)

The script `generate_grid_scenario.py` creates a synthetic $N \times N$ grid road network using SUMO's `netgenerate` tool and populates it with vehicle demand trips using SUMO's `randomTrips.py` utility.

### Vehicle Demand Levels

| Demand Level | `randomTrips` Period (`-p`) | Vehicle Departure Rate | Use Case / Traffic Regime |
|---|---|---|---|
| `light` | `2.0s` | 0.5 vehicles/sec (1,800 veh/hr) | Low-density baseline with minimal queuing or congestion. |
| `moderate` | `1.0s` | 1.0 vehicles/sec (3,600 veh/hr) | Standard urban traffic density with intermittent bottlenecks. |
| `heavy` | `0.5s` | 2.0 vehicles/sec (7,200 veh/hr) | High-density grid inducing significant queues & bottleneck congestion. |

*Note: Demand rates are parameterized via the `--period` flag in `randomTrips.py`, which specifies the average interval in seconds between vehicle departures.*

---

## Command Examples

### 1. Generate Light Demand Grid (5x5)
```bash
python backend/scenario_tools/generate_grid_scenario.py --size 5 --demand-level light
```
Generates scenario at `backend/scenarios/grid_5_light/`.

### 2. Generate Moderate Demand Grid (5x5)
```bash
python backend/scenario_tools/generate_grid_scenario.py --size 5 --demand-level moderate
```
Generates scenario at `backend/scenarios/grid_5_moderate/`.

### 3. Generate Heavy Demand Grid (5x5)
```bash
python backend/scenario_tools/generate_grid_scenario.py --size 5 --demand-level heavy
```
Generates scenario at `backend/scenarios/grid_5_heavy/`.

### Custom Grid Dimensions and Output Path
```bash
python backend/scenario_tools/generate_grid_scenario.py --size 4 --length 250 --lanes 3 --demand-level moderate --seed 42
```

---

## Version Control Policy

> **[IMPORTANT]**
> The generated binary/XML files (`*.net.xml`, `*.rou.xml`, `*.sumocfg`, `*.alt.xml`, `*.trips.xml`) are **ignored by git** (configured in `.gitignore`) and should **NOT** be committed.
> 
> Only the generator scripts (`generate_grid_scenario.py`), documentation (`README.md`), and scenario configuration descriptors (`scenario.yaml`) are version-controlled. The underlying SUMO network and route XML files are generated on demand.
