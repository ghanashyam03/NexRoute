# VSL Finding Interpretation & Literature Reframing

## 1. Code-Level Inspection of VSL Speed-Floor Logic

- **Location**: [`backend/app/traffic_manager.py`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/backend/app/traffic_manager.py#L770-L810)
- **Trigger Condition** (Lines 738–739):
  ```python
  if occupancy > 0.7 or (mean_speed > 0 and speed_limit and mean_speed < speed_limit * 0.5):
      edges_to_optimize.append(edge_id)
  ```
- **Speed Adjustment & Hardcoded Floor** (Lines 794–806):
  ```python
  speed_factor = max(
      min_speed_factor,
      1.0 - (congestion * 0.5 + queue_factor * 0.4 + density_factor * 0.3 + stop_factor * 0.2)
  )
  new_speed = normal_speed * speed_factor
  new_speed = max(3.0, min(new_speed, normal_speed))  # Hardcoded minimum floor of 3.0 m/s
  ```
- **Enforcement** (Line 809):
  ```python
  traci.edge.setMaxSpeed(edge_id, new_speed)
  ```

---

## 2. Evaluation of Three Possible Framings

### Framing (a): "Implementation Bug"
- **Arguments**: Could be argued if the code contains an unintended math error, off-by-one error, or unit mismatch.
- **Evidence Assessment**: **NOT SUPPORTED**. The logic executes precisely as designed: it calculates normalized congestion/density/queue factors, bounds them by `min_speed_factor`, clamps the resulting speed between $3.0\text{ m/s}$ and `normal_speed`, and issues `traci.edge.setMaxSpeed()`. There are no syntax, unit, or logic bugs in the calculation itself.

### Framing (b): "Domain Mismatch, Reportable As-Is"
- **Arguments**: VSL operates as designed, but its underlying paradigm (freeway speed harmonization) is fundamentally ill-suited for short, signalized urban grid links.
- **Evidence Assessment**: **HIGHLY SUPPORTED BY CITATION #1**. 
  - Riehl et al. (2026) establish that in standard Intelligent Transportation Systems (ITS) practice, traffic signal control and perimeter control are urban-context strategies, whereas Variable Speed Limits (VSL) and ramp metering are freeway-context strategies (e.g., Max Pressure/SCOOT for signals vs. ALINEA/HERO for freeways).
  - On short urban grid links ($100–300\text{m}$), lowering speed limits to $3.0\text{ m/s}$ throttles approach speeds. Vehicles cannot clear downstream green light phases in time, resulting in missed green splits and destructive queue spillovers.

### Framing (c): "Needs a Coordination Mechanism, Not a Fix"
- **Arguments**: VSL and dynamic signals operate independently without cross-subsystem communication; VSL has no awareness of signal phase states (green/yellow/red).
- **Evidence Assessment**: **HIGHLY SUPPORTED BY CITATION #2**.
  - MDPI Systems/Sustainability (2026) establishes that coupling multiple traffic controllers without explicit coordination produces conflicting decisions that degrade throughput rather than improve it.
  - In NexRoute, VSL lowers edge speed limits without knowing whether the downstream signal is green or red. A vehicle approaching a green light is forced to slow to $3.0\text{ m/s}$, destroying the signal phase plan calculated by PSO.

---

## 3. Recommended Primary Framing & Paper Narrative

**Recommended Synthesis: Framing (b) + Framing (c)**

> **Primary Recommendation**: Report the finding in the paper as a **genuine, citable scientific contribution**:
> 1. *Domain Mismatch*: Uncoordinated freeway-style VSL applied directly to signalized urban grid networks creates destructive interference with signal-phase clearance (supported by Riehl et al., 2026).
> 2. *Lack of Multi-Controller Coordination*: Uncoordinated coupling of VSL and adaptive signals causes conflicting actions—VSL speed throttling counteracts PSO signal phase allocation (supported by MDPI 2026).
> 3. *Actionable Recommendation*: On urban arterial grids, dynamic signal control should be paired with adaptive vehicle rerouting (`signal_and_routing`), while VSL should either remain disabled or be co-optimized via an explicit signal-aware coordination protocol.
