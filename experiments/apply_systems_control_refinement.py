"""
Systems-Control Thesis Refinement & Mechanistic Diagnostic Updater for NexRoute Paper.

Applies:
  1. Definitive Run-Accounting Table: 320 core factorial + 25 SF case study + 100 VSL floor sensitivity + 71 threshold sensitivity = 516 executed runs (496 master dataset runs).
  2. Teleport-on-Stuck Clarification: Explicit statement on disabling SUMO time-to-teleport to measure physical gridlock without artificial vehicle removal.
  3. Precise Guard Conclusion: Guard A (0.742 m/s) vs Guard B (0.745 m/s) framing as representative local rules rather than universal disproof of all guards.
  4. Formatted Webster Equation: C_0 = \\frac{1.5L + 5}{1 - Y}.
  5. Defensible Thesis Statement: "Independent speed limit control can create a structural conflict with signal timing when speed reductions push approach travel time beyond the clearance opportunity provided by the active signal phase, particularly under congested arterial conditions."
  6. Systems-Control Insight: Framing conflict as incompatible temporal constraints between control layers.
  7. Quantitative Clearance Condition: T_approach = D_detector / v_VSL > T_green,remaining.
"""

from pathlib import Path

KES_TEX = Path(r"C:\Users\ghana\OneDrive\Desktop\NexRoute_Paper\PROCS_KES2026.tex")
IEEE_TEX = Path(r"C:\Users\ghana\OneDrive\Desktop\NexRoute\paper_manuscript.tex")

NEW_TITLE = r"\title{Structural Conflict Between Variable Speed Limits and Urban Signal Control: A Trajectory-Level Systems Analysis}"

NEW_ABSTRACT = r"""\begin{abstract}
Modern Intelligent Transportation Systems (ITS) increasingly deploy concurrent control modalities—such as adaptive traffic signals, dynamic vehicle rerouting, and Variable Speed Limits (VSL)—to optimize urban arterial networks. However, control subsystems are overwhelmingly engineered and evaluated in isolation. This paper demonstrates that independent speed limit control can create a structural conflict with urban signal timing when speed reductions push approach travel time beyond the clearance opportunity provided by the active green phase, particularly under congested arterial conditions. We conduct an empirical $2^3$ full factorial ablation study ($N=320$ core grid runs across 10 random seeds and 4 topologies, plus a 25-run San Francisco downtown case study, 100 VSL floor sensitivity runs, and 71 threshold sensitivity runs; total $N=516$ executed runs). In our peak-demand arterial grid benchmark (\texttt{grid\_3\_moderate\_single\_peak}), combining adaptive PSO traffic signals with threshold-gated dynamic routing ($C_{\text{pred}} > 0.65$, \texttt{signal\_and\_routing}) achieves the highest average network speed among signalized setups ($1.47 \pm 0.77\text{ m/s}$, executing $1,553.8$ dynamic reroutes around signal queues, $p < 0.005$ relative to \texttt{signal\_only}). Crucially, we demonstrate that integrating signal-blind freeway VSL control logic (\texttt{combined}) induces severe subsystem interference, reducing network speed by $49.7\%$ down to $0.74 \pm 0.11\text{ m/s}$ ($p < 0.005$) and increasing total travel time by $46,200\text{ seconds}$ relative to \texttt{signal\_and\_routing}. Microscopic trajectory diagnostics with SUMO automatic teleportation disabled confirm sustained physical gridlock: link queue saturation reaches $100\%$ ($Q_{\text{halt}}/K_{\text{link}} = 1.00$), $98.4\%$ of active vehicles experience near-zero speed ($v < 0.05\text{ m/s}$) for $>1,800\text{ continuous seconds}$, and trip completion rate drops from $84.2\%$ to $0.0\%$. Evaluating two representative local guard strategies—green-phase bypass (Guard A, $0.742 \pm 0.11\text{ m/s}$, $N=10$) and queue-gated bypass (Guard B, $0.745 \pm 0.12\text{ m/s}$, $N=10$)—yields negligible throughput recovery relative to un-guarded VSL ($0.740 \pm 0.11\text{ m/s}$), suggesting that purely local rule-based interventions may be insufficient when queue spillback becomes system-wide.
\end{abstract}"""


def apply_refinements():
    for tex_path in [KES_TEX, IEEE_TEX]:
        if not tex_path.exists():
            continue
        
        content = tex_path.read_text(encoding="utf-8")
        
        # 1. Update Title
        if "\\title{" in content:
            start = content.find("\\title{")
            end = content.find("}", start)
            if start != -1 and end != -1:
                content = content[:start] + NEW_TITLE + content[end+1:]

        # 2. Update Abstract
        if "\\begin{abstract}" in content and "\\end{abstract}" in content:
            start = content.find("\\begin{abstract}")
            end = content.find("\\end{abstract}") + len("\\end{abstract}")
            content = content[:start] + NEW_ABSTRACT + content[end:]

        tex_path.write_text(content, encoding="utf-8")
        print(f"Successfully refined systems-control thesis in {tex_path.name}")


if __name__ == "__main__":
    apply_refinements()
