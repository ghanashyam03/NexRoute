# VSL Signal-Aware Coordination Probe — Exploratory Follow-Up

## 1. Executive Summary & Caveat

This document records the exploratory follow-up probe testing whether a minimal signal-phase-aware guard resolves Variable Speed Limit (VSL) speed-throttling interference on urban grid topologies.

> **EXPLICIT CAVEAT**: This is a small exploratory probe ($N=3-5$ seeds on `grid_3_moderate_single_peak`), **NOT a fully validated architecture fix**. It is labeled as an exploratory probe and is intended for inclusion in the paper's Discussion / Future Work section rather than the main benchmark results.

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

## 3. Empirical Results & Comparison (`grid_3_moderate_single_peak`)

| Condition | Active Subsystems | Average Speed | Total Travel Time | Status / Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **`combined`** | Signals + VSL + Routing (Uncoordinated) | $0.74\text{ m/s}$ | $242,150\text{s}$ | Uncoordinated VSL speed throttling |
| **`vsl_signal_aware`** | Signals + VSL + Routing (Green Bypass Guard) | **$0.81\text{ m/s}$** | **$239,000\text{s}$** | **Marginal gain (+0.07 m/s, -3,150s TTT)** |
| **`signal_and_routing`** | Signals + Routing (NO VSL) | **$3.00\text{ m/s}$** | **$190,500\text{s}$** | **Full performance recovery (>3.7x faster)** |

---

## 4. Key Takeaways for Paper Discussion

1. **Marginal Improvement**: A minimal green-phase speed bypass improves average speed slightly ($0.81\text{ m/s}$ vs $0.74\text{ m/s}$ in `combined`), but fails to restore performance to the $3.00\text{ m/s}$ speed achieved by disabling VSL entirely (`signal_and_routing`).
2. **Scientific Conclusion**: Naive speed bypasses on green approaches are insufficient because queue spillbacks from upstream junctions spill into mid-block links regardless of instantaneous downstream signal phase state.
3. **Future Work Recommendation**: Resolving urban VSL-signal interference requires a full joint co-optimization protocol (e.g. Model Predictive Control or Multi-Agent RL) that co-optimizes signal green splits and VSL speed limits continuously across network links, rather than a local rule-based guard.
