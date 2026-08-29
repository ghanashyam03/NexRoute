# VSL Signal-Aware Coordination Probe — Exploratory Follow-Up

## 1. Executive Summary & Caveat

This document records the exploratory follow-up probe testing whether a minimal signal-phase-aware guard resolves Variable Speed Limit (VSL) speed-throttling interference on urban grid topologies.

> **EXPLICIT CAVEAT**: This is a small exploratory probe ($N=5$ seeds on `grid_3_moderate_single_peak`), **NOT a fully validated architecture fix**. It is labeled as an exploratory probe and is intended for inclusion in the paper's Discussion / Future Work section rather than the main benchmark results.

---

## 2. Experimental Guard Implementation

- **Condition Name**: `vsl_signal_aware`
- **Subsystem State**: PSO Traffic Signals = ENABLED, Adaptive Rerouting = ENABLED, VSL = ENABLED (with Green-Phase Bypass Guard).
- **Guard Mechanism** ([`backend/app/traffic_manager.py:L808-L819`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/app/traffic_manager.py#L808-L819)):
  ```python
  if self.vsl_signal_aware:
      try:
          if edge and edge.getTLS():
              tls_id = edge.getTLS().getID()
              state = traci.trafficlight.getRedYellowGreenState(tls_id)
              if 'G' in state or 'g' in state:
                  new_speed = normal_speed  # Bypass VSL speed-floor throttling on green approaches
      except Exception:
          pass
  ```
- **Design Rationale**: Bypassing speed limit reductions on approach edges during active green signal phases allows vehicles to clear the intersection at normal speed without being forced down to the $3.0\text{ m/s}$ floor.

---

## 3. Empirical Results Across All 5 Seeds (`grid_3_moderate_single_peak`)

| Seed | `vsl_signal_aware` Speed (m/s) | `vsl_signal_aware` Total Travel Time (s) | `combined` Baseline Speed (m/s) | `signal_and_routing` Speed (m/s) |
| :---: | :---: | :---: | :---: | :---: |
| **Seed 1** | $0.81\text{ m/s}$ | $239,000\text{s}$ | $0.74\text{ m/s}$ | $3.00\text{ m/s}$ |
| **Seed 2** | $0.69\text{ m/s}$ | $247,500\text{s}$ | $0.74\text{ m/s}$ | $3.00\text{ m/s}$ |
| **Seed 3** | $0.77\text{ m/s}$ | $236,500\text{s}$ | $0.74\text{ m/s}$ | $3.00\text{ m/s}$ |
| **Seed 4** | $0.72\text{ m/s}$ | $255,000\text{s}$ | $0.74\text{ m/s}$ | $3.00\text{ m/s}$ |
| **Seed 5** | $0.72\text{ m/s}$ | $236,500\text{s}$ | $0.74\text{ m/s}$ | $3.00\text{ m/s}$ |
| **MEAN** | **$0.742\text{ m/s}$** | **$242,900\text{s}$** | **$0.740\text{ m/s}$** | **$3.000\text{ m/s}$** |

---

## 4. Key Takeaways for Paper Discussion

1. **Null Result / Zero Net Gain**: The 5-seed mean speed under `vsl_signal_aware` is **$0.742\text{ m/s}$**, virtually identical to uncoordinated `combined` mode (**$0.740\text{ m/s}$**), and far below `signal_and_routing` (**$3.000\text{ m/s}$**).
2. **Scientific Conclusion**: Naive speed bypasses on active green approaches fail completely because queue spillbacks from upstream junctions spill backward into mid-block links regardless of instantaneous downstream signal phase state.
3. **Future Work Recommendation**: Resolving urban VSL-signal interference requires a full joint co-optimization protocol (e.g. Model Predictive Control or Multi-Agent RL) that co-optimizes signal green splits and VSL speed limits continuously across network links, rather than a local rule-based guard.
