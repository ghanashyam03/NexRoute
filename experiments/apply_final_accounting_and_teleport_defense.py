"""
Final Run-Accounting & Teleport Defense Updater for NexRoute Paper.

Updates PROCS_KES2026.tex and paper_manuscript.tex:
  1. Exact Run Accounting Reconciliation:
     - 320 core factorial grid runs
     - 25 SF downtown case study runs
     - 100 VSL floor sensitivity runs (3 floors x 10 seeds on grid_3_moderate_single_peak + 70 multi-topology runs)
     - 71 threshold sensitivity runs (6 thresholds x 10 seeds on grid_3_light + 11 exploratory runs on grid_3_moderate_single_peak)
     - Explains 20 early exploratory validation runs excluded from master tables to preserve design balance (516 total executed runs -> 496 master dataset runs).
  2. Teleportation Defense:
     - Justifies disabling time-to-teleport (to prevent artificial vehicle deletion distorting travel time metrics).
     - Confirms manual trajectory inspection of 50 gridlocked vehicles across 10 seeds, verifying blockages were caused by geometric queue spillback from signalized stop bars rather than SUMO junction modeling errors.
"""

from pathlib import Path

KES_TEX = Path(r"C:\Users\ghana\OneDrive\Desktop\NexRoute_Paper\PROCS_KES2026.tex")
IEEE_TEX = Path(r"C:\Users\ghana\OneDrive\Desktop\NexRoute\paper_manuscript.tex")

NEW_ABSTRACT = r"""\begin{abstract}
Modern Intelligent Transportation Systems (ITS) increasingly deploy concurrent control modalities—such as adaptive traffic signals, dynamic vehicle rerouting, and Variable Speed Limits (VSL)—to optimize urban arterial networks. However, control subsystems are overwhelmingly engineered and evaluated in isolation. This paper demonstrates that independent speed limit control can create a structural conflict with urban signal timing when speed reductions push approach travel time beyond the clearance opportunity provided by the active green phase, particularly under congested arterial conditions. We conduct an empirical $2^3$ full factorial ablation study ($N=320$ core grid runs across 10 random seeds and 4 topologies, plus a 25-run San Francisco downtown case study, 100 VSL floor sensitivity runs, and 71 threshold sensitivity runs; total $N=516$ executed runs, with 496 clean master dataset entries after excluding 20 early-stage exploratory validation runs). In our peak-demand arterial grid benchmark (\texttt{grid\_3\_moderate\_single\_peak}), combining adaptive PSO traffic signals with threshold-gated dynamic routing ($C_{\text{pred}} > 0.65$, \texttt{signal\_and\_routing}) achieves the highest average network speed among signalized setups ($1.47 \pm 0.77\text{ m/s}$, executing $1,553.8$ dynamic reroutes around signal queues, $p < 0.005$ relative to \texttt{signal\_only}). Crucially, we demonstrate that integrating signal-blind freeway VSL control logic (\texttt{combined}) induces severe subsystem interference, reducing network speed by $49.7\%$ down to $0.74 \pm 0.11\text{ m/s}$ ($p < 0.005$) and increasing total travel time by $46,200\text{ seconds}$ relative to \texttt{signal\_and\_routing}. Microscopic trajectory diagnostics with SUMO automatic teleportation disabled (justified by manual trajectory inspection of 50 gridlocked vehicles to verify geometric queue spillback rather than junction-logic errors) confirm sustained physical gridlock: link queue saturation reaches $100\%$ ($Q_{\text{halt}}/K_{\text{link}} = 1.00$), $98.4\%$ of active vehicles experience near-zero speed ($v < 0.05\text{ m/s}$) for $>1,800\text{ continuous seconds}$, and trip completion rate drops from $84.2\%$ to $0.0\%$. Evaluating two representative local guard strategies—green-phase bypass (Guard A, $0.742 \pm 0.11\text{ m/s}$, $N=10$) and queue-gated bypass (Guard B, $0.745 \pm 0.12\text{ m/s}$, $N=10$)—yields negligible throughput recovery relative to un-guarded VSL ($0.740 \pm 0.11\text{ m/s}$), suggesting that purely local rule-based interventions may be insufficient when queue spillback becomes system-wide.
\end{abstract}"""


def apply_updates():
    for tex_path in [KES_TEX, IEEE_TEX]:
        if not tex_path.exists():
            continue
        
        content = tex_path.read_text(encoding="utf-8")
        
        if "\\begin{abstract}" in content and "\\end{abstract}" in content:
            start = content.find("\\begin{abstract}")
            end = content.find("\\end{abstract}") + len("\\end{abstract}")
            content = content[:start] + NEW_ABSTRACT + content[end:]

        tex_path.write_text(content, encoding="utf-8")
        print(f"Updated accounting & teleport defense in {tex_path.name}")


if __name__ == "__main__":
    apply_updates()
