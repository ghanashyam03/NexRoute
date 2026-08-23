# NexRoute Full-Scale Multi-Scenario Ablation Sweep Plan

This document outlines the execution plan, seed sample size justification, ready-to-run CLI command sequence, and wall-clock time estimation for the full-scale research study across all network scenarios in `backend/scenarios/`.

---

## 1. Scenario Inventory & Seed Count Justification

### Scenario Set
Inspected directory `backend/scenarios/`:
1. `grid_3_light`: 3x3 synthetic grid under light uniform demand.
2. `grid_3_moderate_single_peak`: 3x3 synthetic grid under single-peak bell-curve demand.
3. `grid_3_moderate_two_peak`: 3x3 synthetic grid under bimodal morning/evening peak demand.
4. `grid_5_moderate`: 5x5 synthetic grid under moderate uniform demand.
5. `real_sf_downtown`: Real-world OpenStreetMap (OSM) San Francisco downtown corridor topology.

*(Note: `default` is a dummy alias, and `user_custom_osm` is a template directory for user uploads).*

### Recommended Seed Count: $N = 10$ Seeds per Condition per Scenario
- **Statistical Power Rationale**: `experiments/analyze_results.py` automatically flags statistical comparison pairs with a `use_with_caution_small_n` caution flag whenever paired sample size $N < 10$.
- **Sample Size Margin**: $N = 10$ shared seeds per condition guarantees $N = 10$ paired samples per comparison, clearing the small-sample threshold with zero caution flags while maintaining manageable multi-hour wall-clock execution time.

---

## 2. Command Sequence for Full-Scale Sweep Execution

### Step A: Sanity-Check Dry Run Command
Run this first to verify all 250 run combinations without launching SUMO processes:

```bash
python experiments/run_ablation_sweep.py \
  --scenarios grid_3_light grid_3_moderate_single_peak grid_3_moderate_two_peak grid_5_moderate real_sf_downtown \
  --seeds 1,2,3,4,5,6,7,8,9,10 \
  --dry-run
```

### Step B: Full Production Sweep Command (Multi-Hour Unattended Run)
Execute this command to launch the full sweep across all scenarios, conditions, and seeds:

```bash
python experiments/run_ablation_sweep.py \
  --scenarios grid_3_light grid_3_moderate_single_peak grid_3_moderate_two_peak grid_5_moderate real_sf_downtown \
  --seeds 1,2,3,4,5,6,7,8,9,10 \
  --output-dir experiments/results
```

---

## 3. Wall-Clock Execution Time & Resumability Estimate

### Combination Count Breakdown
- **5 Scenarios**: `grid_3_light`, `grid_3_moderate_single_peak`, `grid_3_moderate_two_peak`, `grid_5_moderate`, `real_sf_downtown`.
- **5 Conditions per Scenario**: `baseline`, `signal_only`, `vsl_only`, `routing_only`, `combined`.
- **10 Seeds per Cell**: `1, 2, 3, 4, 5, 6, 7, 8, 9, 10`.
- **Total Simulation Runs**: $5 \text{ scenarios} \times 5 \text{ conditions} \times 10 \text{ seeds} = \mathbf{250 \text{ runs}}$.

### Execution Time Estimate
- **Baseline / VSL-Only / Routing-Only Runs**: $\approx 10\text{ seconds}$ per run ($150 \text{ runs} \times 10\text{s} = 1,500\text{s}$).
- **Signal-Only / Combined Runs (PSO Optimization)**: $\approx 70\text{ seconds}$ per run ($100 \text{ runs} \times 70\text{s} = 7,000\text{s}$).
- **Total Estimated Wall-Clock Time**: $1,500\text{s} + 7,000\text{s} = 8,500\text{ seconds} \approx \mathbf{2.36\text{ hours}}$.

### Resumability Guarantee
The sweep orchestrator (`experiments/run_ablation_sweep.py`) records all successful runs in `experiments/results/sweep_manifest.jsonl`. If interrupted at any point (e.g. CTRL+C, power loss, or session timeout), re-running the exact command will automatically skip all completed successful runs and resume cleanly from the last incomplete run.
