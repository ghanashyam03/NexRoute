# NexRoute Research Methodology & Experimental Protocol

This document provides a comprehensive, rigorous specification of the research design, ablation matrix, statistical framework, scenario topologies, and experimental limitations for **NexRoute**—an open-source platform for multi-agent urban traffic signal timing, variable speed limit (VSL), and dynamic route optimization.

---

## 1. Research Question & Primary Objectives

The primary scientific objective of NexRoute is to evaluate the isolated and synergistic contributions of intelligent transportation system (ITS) control mechanisms in urban road networks. Specifically, this research addresses two core questions:

1. **Component Attribution**: Which individual subsystem—traffic signal timing optimization, variable speed limits (VSL), or dynamic vehicle rerouting—drives the greatest reduction in urban traffic congestion and travel delay?
2. **Control Synergies**: Does combining all three subsystems yield statistically significant performance gains beyond the single best-performing isolated component?

---

## 2. Experimental Conditions (Ablation Matrix)

To systematically decompose performance contributions, NexRoute defines a 5-condition ablation matrix. As implemented in [`experiments/run_ablation_sweep.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/experiments/run_ablation_sweep.py), each cell invokes the headless batch simulation runner ([`backend/run.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/run.py)) with exact command-line flag configurations:

| Condition Name | Subsystem Flags (`--enable-*`) | Signal Strategy (`--signal-strategy`) | Routing Strategy (`--routing-strategy`) | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`baseline`** | `--no-enable-signals --no-enable-vsl --no-enable-routing` | `webster` | `static` | Uncoordinated baseline: Fixed-time Webster signal timing, no VSL, static Dijkstra shortest-path routing. |
| **`signal_only`** | `--enable-signals --no-enable-vsl --no-enable-routing` | `pso` | `static` | Isolated signal optimization: Particle Swarm Optimization (PSO) adaptive green phase allocation, static routing. |
| **`vsl_only`** | `--no-enable-signals --enable-vsl --no-enable-routing` | `webster` | `static` | Isolated VSL optimization: Dynamic edge speed limit adjustments based on predicted congestion, fixed signal timing. |
| **`routing_only`** | `--no-enable-signals --no-enable-vsl --enable-routing` | `webster` | `adaptive` | Isolated dynamic routing: PSO-weighted dynamic rerouting around congested links, fixed signal timing. |
| **`signal_and_routing`** | `--enable-signals --no-enable-vsl --enable-routing` | `pso` | `adaptive` | Dual signal + routing control: Concurrent PSO signal timing and dynamic route optimization (VSL disabled). |
| **`signal_and_vsl`** | `--enable-signals --enable-vsl --no-enable-routing` | `pso` | `static` | Dual signal + VSL control: Concurrent PSO signal timing and VSL speed limit adjustments (routing static). |
| **`vsl_and_routing`** | `--no-enable-signals --enable-vsl --enable-routing` | `webster` | `adaptive` | Dual VSL + routing control: Concurrent VSL speed control and dynamic route optimization (Webster signals). |
| **`combined`** | `--enable-signals --enable-vsl --enable-routing` | `pso` | `adaptive` | Full integrated system: Concurrent PSO signal timing, VSL speed control, and dynamic route optimization. |

### Quoted Command-Line Invocations from Code
As defined in `ABLATION_CONDITIONS` within `experiments/run_ablation_sweep.py`:

```python
ABLATION_CONDITIONS = {
    "baseline": {
        "enable_signals": False, "signal_strategy": "webster",
        "enable_vsl": False, "enable_routing": False, "routing_strategy": "static"
    },
    "signal_only": {
        "enable_signals": True, "signal_strategy": "pso",
        "enable_vsl": False, "enable_routing": False, "routing_strategy": "static"
    },
    "vsl_only": {
        "enable_signals": False, "signal_strategy": "webster",
        "enable_vsl": True, "enable_routing": False, "routing_strategy": "static"
    },
    "routing_only": {
        "enable_signals": False, "signal_strategy": "webster",
        "enable_vsl": False, "enable_routing": True, "routing_strategy": "adaptive"
    },
    "signal_and_routing": {
        "enable_signals": True, "signal_strategy": "pso",
        "enable_vsl": False, "enable_routing": True, "routing_strategy": "adaptive"
    },
    "signal_and_vsl": {
        "enable_signals": True, "signal_strategy": "pso",
        "enable_vsl": True, "enable_routing": False, "routing_strategy": "static"
    },
    "vsl_and_routing": {
        "enable_signals": False, "signal_strategy": "webster",
        "enable_vsl": True, "enable_routing": True, "routing_strategy": "adaptive"
    },
    "combined": {
        "enable_signals": True, "signal_strategy": "pso",
        "enable_vsl": True, "enable_routing": True, "routing_strategy": "adaptive"
    }
}
```

---

## 3. Scenario Topology & Demand Profiles

NexRoute evaluates scenarios under [`backend/scenarios/`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/scenarios/), supporting synthetic grid networks and real-world OpenStreetMap (OSM) extractions.

### Scenario Categorization & Parameters

1. **Synthetic Grid Topologies**:
   - Generated via [`backend/scenario_tools/generate_grid_scenario.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/scenario_tools/generate_grid_scenario.py) using SUMO `netgenerate`.
   - Grid sizes: $3 \times 3$ and $5 \times 5$ intersection topologies ($200\text{m}$ edge length, 2 lanes per direction).
   - Demand levels: `light` ($0.2\text{ veh/s}$ generation rate), `moderate` ($0.5\text{ veh/s}$), and `heavy` ($0.8\text{ veh/s}$).

2. **Multi-Level Demand Shapes**:
   - Implemented via [`backend/scenario_tools/demand_shapes.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/scenario_tools/demand_shapes.py).
   - `flat`: Constant flow rate across full simulation duration.
   - `single_peak`: Gaussian peak flow (center at $t=1800\text{s}$, peak multiplier $2.5\times$).
   - `two_peak`: Bimodal morning/evening peak shape (peaks at $t=1200\text{s}$ and $t=2700\text{s}$, peak multiplier $2.2\times$).

3. **Real-World OpenStreetMap Topologies**:
   - Pipeline [`backend/scenario_tools/import_osm_scenario.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/scenario_tools/import_osm_scenario.py) converts raw OSM `.osm` files via `netconvert`.
   - Built-in scenarios: `real_sf_downtown` (San Francisco downtown corridor) and `user_custom_osm`.

---

## 4. Sample Size & Seed Alignment Protocol

- **Seed Alignment**: All 5 experimental conditions within a scenario share an identical sequence of random seeds ($1, 2, \dots, N$). Global seeding ([`backend/app/seeding.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/app/seeding.py)) controls Python `random`, NumPy `np.random`, and SUMO simulation vehicle generation.
- **Rationale**: Seed alignment produces paired observations under identical stochastic vehicle departure schedules, eliminating arrival order variance between conditions and dramatically increasing statistical power.
- **Minimum Seed Threshold**: Set to `--min-seeds-per-cell 5` in [`experiments/aggregate_results.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/experiments/aggregate_results.py) and `--min-pairs 5` in [`experiments/analyze_results.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/experiments/analyze_results.py).

---

## 5. Statistical Analysis Methodology

As implemented in [`experiments/analyze_results.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/experiments/analyze_results.py), every non-baseline condition is rigorously compared against `baseline` and against isolated components:

1. **Parametric Test**: Seed-aligned paired Student's $t$-test evaluating $H_0: \mu_{\text{diff}} = 0$.
2. **Non-Parametric Test**: Seed-aligned Wilcoxon signed-rank test cross-checking normality assumptions.
3. **Effect Size**: Standardized Cohen's $d$ for paired samples:
   $$d = \frac{\bar{D}}{s_D}$$
   where $\bar{D}$ is the mean of seed-level differences and $s_D$ is the standard deviation of differences.
4. **Bootstrap Confidence Intervals**: 10,000 empirical bootstrap resamples (`--n-bootstraps 10000`) computing 95% bias-corrected percentile confidence intervals ($[CI_{\text{lower}}, CI_{\text{upper}}]$) for Cohen's $d$.
5. **False Discovery Rate (FDR) Correction**: Benjamini-Hochberg procedure adjusting raw $p$-values across all metric comparisons ($\alpha = 0.05$).
6. **Small-Sample Power Warning Flag**: Comparisons with $n < 5$ pairs are automatically flagged with `caution_flag = "use_with_caution_small_n"`, highlighting potential low-power limitations in generated forest plots.

---

## 6. Known Limitations & Testing Gaps

1. **Simulation-Only Environment**: All findings are derived from SUMO microscopic traffic simulation runs; physical real-world urban deployment validation has not been performed.
2. **Heuristic PSO Coefficients**: The Particle Swarm Optimizer hyperparameters ($w=0.7, c1=1.5, c2=1.5$) and routing objective weights in [`backend/app/optimizer.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/app/optimizer.py) are hand-tuned heuristic values rather than empirical parameters estimated from field data.
3. **Congestion Prediction Weight Verification**: Empirical source-code auditing of `_predict_congestion` ([`backend/app/traffic_manager.py:L383-L389`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/app/traffic_manager.py#L383)) verified that linear prediction factor weights ($0.25 + 0.20 + 0.15 + 0.15 + 0.10 + 0.10 + 0.05$) sum to **exactly 1.00**, confirming mathematical model integrity.
4. **Asymmetric Bootstrap Errorbar Artifacts**: When running sweeps on small seed counts ($n < 5$) or short durations, bootstrap resample standard error estimation may produce asymmetric confidence intervals where Cohen's $d$ lies slightly outside $[CI_{\text{lower}}, CI_{\text{upper}}]$, causing visualization tools to flag errorbar bounds.
5. **TraCI Live State Coupling Gaps**: As documented in [`TODO_TESTING_GAPS.md`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/TODO_TESTING_GAPS.md), methods `_update_vehicle_states`, `_apply_signal_optimization`, and `_apply_vsl_optimization` require active SUMO TraCI API connections and are not isolated behind mock interfaces.
6. **VSL Heuristic Parameter Hand-Tuning**: As implemented in [`backend/app/traffic_manager.py:L794-L806`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/app/traffic_manager.py#L794-L806), the VSL minimum speed floor of $3.0\text{ m/s}$ ($\approx 10.8\text{ km/h}$) and linear penalty weights ($0.5, 0.4, 0.3, 0.2$) are hand-tuned heuristic constants without formal derivation, analogous to the congestion predictor weights. Uncoordinated VSL has no awareness of downstream signal phases, which is evaluated as a primary scientific finding regarding multi-controller interference.
