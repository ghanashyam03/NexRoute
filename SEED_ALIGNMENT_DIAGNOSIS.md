# Seed Alignment & Dataset Completeness Diagnosis

## 1. Per-(Scenario, Condition) Exact Seed Set Inventory

Extracted directly from [`experiments/results/aggregated_results.parquet`](file:///c:/Users/ghana/OneDrive/Desktop/NexRoute/experiments/results/aggregated_results.parquet):

| Scenario | Condition | Seed Count ($N$) | Exact Seed Set Values | Status |
| :--- | :--- | :---: | :--- | :--- |
| **`grid_3_light`** | `baseline` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `signal_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `vsl_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `routing_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `combined` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `signal_and_routing` | **0** | `[]` | **MISSING** |
| | `signal_and_vsl` | **0** | `[]` | **MISSING** |
| | `vsl_and_routing` | **0** | `[]` | **MISSING** |
| **`grid_3_moderate_single_peak`** | `baseline` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `signal_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `vsl_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `routing_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `combined` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `signal_and_routing` | **2** | `[1, 2]` | **UNDERPOWERED** |
| | `signal_and_vsl` | **0** | `[]` | **MISSING** |
| | `vsl_and_routing` | **1** | `[1]` | **UNDERPOWERED** |
| **`grid_3_moderate_two_peak`** | `baseline` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `signal_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `vsl_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `routing_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `combined` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `signal_and_routing` | **0** | `[]` | **MISSING** |
| | `signal_and_vsl` | **0** | `[]` | **MISSING** |
| | `vsl_and_routing` | **0** | `[]` | **MISSING** |
| **`grid_5_moderate`** | `baseline` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `signal_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `vsl_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `routing_only` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `combined` | 10 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | Complete |
| | `signal_and_routing` | **0** | `[]` | **MISSING** |
| | `signal_and_vsl` | **0** | `[]` | **MISSING** |
| | `vsl_and_routing` | **0** | `[]` | **MISSING** |
| **`real_sf_downtown`** | `baseline` | 2 | `[1, 2]` | Case Study |
| | `signal_only` | 1 | `[1]` | Case Study |
| | `vsl_only` | 1 | `[1]` | Case Study |
| | `routing_only` | 1 | `[1]` | Case Study |
| | `combined` | 1 | `[1]` | Case Study |

---

## 2. Root Cause Determination

**Conclusion**: **Situation (a) — Genuinely few total runs exist for the dual conditions.**

- The primary 5 conditions (`baseline`, `signal_only`, `vsl_only`, `routing_only`, `combined`) were fully evaluated on target seed set `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` ($N=10$ seeds per cell) across all 4 synthetic grid scenarios.
- The 3 dual-component conditions (`signal_and_routing`, `signal_and_vsl`, `vsl_and_routing`) were added in a recent extension and were only partially executed ($N=1-2$ seeds on `grid_3_moderate_single_peak`, $N=0$ on all other scenarios).
- Therefore, to achieve a fully powered, uniform $2^3$ factorial design with $N=10$ seeds per cell across all 4 synthetic scenarios, we must top up the missing dual-component cells for seeds 1 through 10.
