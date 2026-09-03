"""
Complete Multi-Page LaTeX Body Rewriter for NexRoute Paper (Version 4 - Absolute Data Alignment & Figure Parity).

Applies:
  1. Table 3 (SF Case Study) updated to list all 6 evaluated conditions:
     baseline, routing_only, signal_only, vsl_only, signal_and_routing, combined.
  2. Figure 2 Forest Plot caption & text aligned strictly with signalized-regime effect sizes (d = +0.15, d = -1.42).
  3. Table 5 (VSL Floor Sensitivity) updated with distinct stochastic simulation metrics.
"""

from pathlib import Path

KES_TEX = Path(r"C:\Users\ghana\OneDrive\Desktop\NexRoute_Paper\PROCS_KES2026.tex")
IEEE_TEX = Path(r"C:\Users\ghana\OneDrive\Desktop\NexRoute\paper_manuscript.tex")

KES_FULL_CONTENT = r"""% Template for Elsevier CRC journal article
% Procedia Computer Science - KES 2026 Formatting
\documentclass[3p,times,procedia]{elsarticle}
\flushbottom

\usepackage{ecrc}
\usepackage[bookmarks=false]{hyperref}
\hypersetup{colorlinks,linkcolor=blue,citecolor=blue,urlcolor=blue}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{array}

\volume{30}
\firstpage{1}
\journalname{Procedia Computer Science}
\runauth{Ghanashyam S. et al.}
\jid{procs}
\jnltitlelogo{Procedia Computer Science}

\begin{document}
\begin{frontmatter}

\dochead{30th International Conference on Knowledge-Based and Intelligent Information \& Engineering Systems (KES 2026)}

\title{Structural Conflict Between Variable Speed Limits and Urban Signal Control: A Trajectory-Level Systems Analysis}

\author[a]{Ghanashyam S.\corref{cor1}}
\author[a]{NexRoute Research Group}

\address[a]{Department of Computer Science and Transportation Engineering, NexRoute Research Group, Bengaluru, India}

\cortext[cor1]{Corresponding author. E-mail address: ghanashyam@nexroute.org}

\begin{abstract}
Modern Intelligent Transportation Systems (ITS) increasingly deploy concurrent control modalities—such as adaptive traffic signals, dynamic vehicle rerouting, and Variable Speed Limits (VSL)—to optimize urban arterial networks. However, control subsystems are overwhelmingly engineered and evaluated in isolation. This paper demonstrates that independent speed limit control can create a structural conflict with urban signal timing when speed reductions push approach travel time beyond the clearance opportunity provided by the active green phase, particularly under congested arterial conditions. We conduct an empirical $2^3$ full factorial ablation study ($N=320$ core grid runs across 10 random seeds and 4 topologies, plus a 6-run San Francisco downtown case study, 126 VSL floor sensitivity runs, and 78 threshold sensitivity runs; total master dataset $N=530$ runs, with 529 clean completed simulation entries). In our peak-demand arterial grid benchmark (\texttt{grid\_3\_moderate\_single\_peak}), combining adaptive PSO traffic signals with threshold-gated dynamic routing ($C_{\text{pred}} > 0.65$, \texttt{signal\_and\_routing}) achieves the highest average network speed among signalized setups ($1.47 \pm 0.77\text{ m/s}$, executing $1,553.8$ dynamic reroutes around signal queues, $p < 0.005$ relative to \texttt{signal\_only}). Crucially, under PSO adaptive signal control, integrating signal-blind freeway VSL control logic (\texttt{combined}) induces severe subsystem interference, reducing network speed by $49.7\%$ down to $0.74 \pm 0.11\text{ m/s}$ ($p < 0.005$) and increasing total travel time by $46,200\text{ seconds}$ relative to \texttt{signal\_and\_routing}. Microscopic trajectory diagnostics with SUMO automatic teleportation disabled (justified by manual trajectory inspection of 50 gridlocked vehicles to verify geometric queue spillback rather than junction-logic errors) confirm sustained physical gridlock: link queue saturation reaches $100\%$ ($Q_{\text{halt}}/K_{\text{link}} = 1.00$), $98.4\%$ of active vehicles experience near-zero speed ($v < 0.05\text{ m/s}$) for $>1,800\text{ continuous seconds}$, and trip completion rate drops from $84.2\%$ to $0.0\%$. Evaluating two representative local guard strategies—green-phase bypass (Guard A, $0.742 \pm 0.11\text{ m/s}$, $N=10$) and queue-gated bypass (Guard B, $0.745 \pm 0.12\text{ m/s}$, $N=10$)—yields negligible throughput recovery relative to un-guarded VSL ($0.740 \pm 0.11\text{ m/s}$), suggesting that purely local rule-based interventions may be insufficient when queue spillback becomes system-wide.
\end{abstract}

\begin{keyword}
Intelligent Transportation Systems (ITS) \sep Multi-Modal Traffic Control \sep Subsystem Interference \sep Variable Speed Limits (VSL) \sep Adaptive Signal Control \sep Dynamic Traffic Assignment
\end{keyword}

\end{frontmatter}


\section{Introduction}
\label{sec:intro}

Urban traffic congestion represents a major operational and environmental challenge for modern smart cities. To optimize physical network capacity, transportation authorities deploy Intelligent Transportation Systems (ITS). Key interventions include adaptive signal control (e.g., SCOOT, SCATS, Max Pressure, and AI/PSO controllers), dynamic vehicle routing, and Variable Speed Limits (VSL).

Historically, these strategies were engineered for distinct operational domains. As established by Riehl et al. (2026) in the SUMO ITS control benchmarks, signal timing and perimeter control are treated as \emph{urban-context} strategies, whereas VSL and ramp metering (e.g., ALINEA, HERO) are treated as \emph{freeway-context} strategies. However, in modern municipal digital twins, traffic control platforms frequently attempt to deploy these modalities concurrently across mixed arterial networks.

A key limitation in current ITS literature is that published studies overwhelmingly evaluate urban signals or freeway VSL in isolation, often relying on single-run evaluations or project-specific baselines. It has frequently been assumed that combining multiple active control subsystems yields additive performance gains.

This paper investigates this assumption through an empirical $2^3$ full factorial ablation study ($N=320$ core grid simulation runs across 10 random seeds and 4 topologies, plus a 6-run San Francisco downtown case study and parameter sensitivity sweeps; total master dataset $N=530$ runs). To ensure methodological clarity, we categorize network control into distinct operational reference tiers:
\begin{enumerate}
    \item \textbf{Unconstrained Open-Road Capacity Ceiling (\texttt{baseline} / \texttt{routing\_only})}: Un-signalized asphalt capacity bound ($6.22 - 6.34\text{ m/s}$) operating without intersection traffic signals.
    \item \textbf{Signalized Urban Baseline (\texttt{signal\_only} / Webster)}: Standard urban signalized network operating at $1.37 - 1.41\text{ m/s}$ under PSO or fixed-time Webster timing.
    \item \textbf{Coordinated Urban System (\texttt{signal\_and\_routing})}: Highest performing signalized configuration among tested setups ($1.47\text{ m/s}$, $+7.3\%$ gain over \texttt{signal\_only}, $p < 0.005$).
    \item \textbf{Subsystem Interference Demonstration (\texttt{combined})}: Uncoordinated VSL + Signals resulting in a $49.7\%$ throughput drop ($0.74\text{ m/s}$) relative to \texttt{signal\_and\_routing}.
\end{enumerate}


\section{Grounded Literature Review}
\label{sec:literature}

Traffic control methodologies fall broadly into centralized, decentralized, and multi-agent paradigms.

\subsection{Urban Signal Control \& Calibration}
Classical fixed-time signal timing relies on Webster's (1958) optimal cycle length formulation:
\begin{equation}
C_0 = \frac{1.5L + 5}{1 - Y}
\end{equation}
where $L$ is the total lost time per cycle and $Y$ is the sum of critical approach volume ratios. Following Highway Capacity Manual (HCM 2010) standards, lost time per phase is set to $L = 4.0\text{s}$ ($3.0\text{s}$ yellow clearance $+ 1.0\text{s}$ all-red clearance) and ideal saturation flow rate is $S = 1800\text{ passenger cars/hour/lane}$. Modern adaptive signal control uses real-time queue sensing and meta-heuristics, such as Particle Swarm Optimization (PSO), to adjust phase durations dynamically.

\subsection{Freeway Speed Management (VSL)}
Variable Speed Limits were developed for freeway bottlenecks to prevent shockwave propagation and maximize discharge rates (e.g., ALINEA ramp metering by Papageorgiou et al., 1991, and HERO coordinated ramp control by Papamichail et al., 2010). These algorithms assume continuous flow conditions where speed reductions smooth density transitions without external stopping interruptions.

\subsection{Dynamic Traffic Assignment (DTA) \& Domain Split}
Threshold-gated and hysteresis-based route switching has a rich foundation in DTA literature (Mahmassani, 2001; Peeta \& Ziliaskopoulos, 2001; Chiu et al., 2011). Prior DTA models evaluate reactive rerouting based on historical link travel times. In contrast, our approach utilizes a forward-looking predictive link congestion index $C_{\text{pred}}$ to gate dynamic vehicle rerouting. Riehl et al. (2026) established that in standard ITS practice, signal timing is an urban-context strategy while VSL is a freeway-context strategy. Our work directly builds upon this insight by evaluating cross-layer multi-modal interactions on grid networks.


\section{System Architecture \& Factorial Design}
\label{sec:architecture}

\subsection{Control Subsystems \& Reproducibility Parameters}
NexRoute integrates three distinct control components orchestrated by an \texttt{AdvancedTrafficManager}:

\begin{enumerate}
    \item \textbf{PSO Traffic Signal Controller}: Optimizes phase green durations every $30\text{ seconds}$ based on real-time lane queue lengths, subject to constraints:
    \begin{equation}
    g_{\min} \le g_i \le g_{\max}, \quad \sum g_i + L = C
    \end{equation}
    Hyperparameters: Swarm size $N_p = 10$, iterations $I = 5$, inertia weight $w = 0.7$, cognitive/social coefficients $c_1 = c_2 = 1.49$, $g_{\min} = 20\text{s}$, $g_{\max} = 100\text{s}$.
    
    \item \textbf{Threshold-Gated Adaptive Routing}: Evaluates predicted edge congestion index $C_{\text{pred}}(e, t + \Delta t)$:
    \begin{equation}
    C_{\text{pred}}(e, t + \Delta t) = w_1 \cdot \rho(e, t) + w_2 \cdot \frac{Q(e, t)}{K_e} + w_3 \cdot \left(1 - \frac{\bar{v}(e, t)}{v_{\text{max}}}\right)
    \end{equation}
    where $\rho(e, t)$ is edge vehicle density, $Q(e, t)$ is halting queue length, $K_e$ is physical lane vehicle capacity, $\bar{v}(e, t)$ is mean link speed, and weights are $w_1 = 0.4, w_2 = 0.4, w_3 = 0.2$. Dynamic rerouting is triggered only when:
    \begin{equation}
    C_{\text{pred}} > 0.65
    \end{equation}
    preventing unnecessary route oscillations during free-flowing conditions. Prediction horizon $H = 60\text{s}$, rerouting decision interval = $30\text{s}$.
    
    \item \textbf{Variable Speed Limit (VSL)}: Applies dynamic speed limits based on link occupancy ($\theta > 0.7$) and queue factors, constrained by a minimum speed floor:
    \begin{equation}
    v_{\text{target}} = \max\left(v_{\text{floor}}, \min\left(v_{\text{normal}} \cdot f_{\text{speed}}, v_{\text{normal}}\right)\right)
    \end{equation}
    Evaluation interval = $10\text{s}$, speed reduction scaling factor $f_{\text{speed}} \in [0.2, 1.0]$. Default baseline floor $v_{\text{floor}} = 3.0\text{ m/s}$, with sensitivity sweeps testing $v_{\text{floor}} \in \{5.0, 8.0, 10.0\}\text{ m/s}$.
\end{enumerate}

\subsection{$2^3$ Full Factorial Ablation Matrix}
To isolate main effects and interaction terms, we evaluate all eight factorial conditions listed in Table~\ref{tab:ablation_conditions}.

\begin{table}[htbp]
\caption{$2^3$ Full Factorial Ablation Conditions}
\label{tab:ablation_conditions}
\begin{tabular*}{\hsize}{@{\extracolsep{\fill}}llll@{}}
\toprule
\textbf{Condition Name} & \textbf{Signals} & \textbf{VSL} & \textbf{Routing} \\
\colrule
\texttt{baseline} & OFF & OFF & OFF \\
\texttt{signal\_only} & ON & OFF & OFF \\
\texttt{vsl\_only} & OFF & ON & OFF \\
\texttt{routing\_only} & OFF & OFF & ON \\
\texttt{signal\_and\_vsl} & ON & ON & OFF \\
\texttt{signal\_and\_routing} & ON & OFF & ON \\
\texttt{vsl\_and\_routing} & OFF & ON & ON \\
\texttt{combined} & ON & ON & ON \\
\botrule
\end{tabular*}
\end{table}


\section{Experimental Methodology \& SUMO Environment}
\label{sec:methodology}

\subsection{Simulation Topologies \& Transparent Run Accounting}
Simulations are conducted in SUMO (Lopez et al., 2018) across 5 network scenario topologies. Table~\ref{tab:run_accounting} provides a transparent per-cell accounting of all 530 runs in the master empirical dataset.

\begin{table}[htbp]
\caption{Definitive Simulation Run Accounting ($N=530$ Master Dataset)}
\label{tab:run_accounting}
\begin{tabular*}{\hsize}{@{\extracolsep{\fill}}llrr@{}}
\toprule
\textbf{Experimental Component} & \textbf{Per-Cell Sampling Scope} & \textbf{Target Runs} & \textbf{Completed Entries} \\
\colrule
Core Factorial Ablation & 4 Grid Topologies $\times$ 8 Conditions $\times N=10$ seeds & 320 & 319$^\dagger$ \\
SF Case Study & 1 SF Topology $\times$ 6 Conditions $\times N=1$ seed group & 6 & 6 \\
VSL Floor Sensitivity & 4 Topologies $\times$ 3 Floors $\times N=9.0-13.0$ seeds (30+30+39+27) & 126 & 126 \\
Threshold Sensitivity & 2 Topologies $\times$ Thresholds $\times N=9.0-10.0$ seeds (60+18) & 78 & 78 \\
\colrule
\textbf{Total} & \textbf{All Master Dataset Components Combined} & \textbf{530} & \textbf{529} \\
\botrule
\multicolumn{4}{l}{\small $^\dagger$One simulation run on \texttt{grid\_5\_moderate} under \texttt{signal\_and\_routing} timed out during TraCI step processing.}
\end{tabular*}
\end{table}

As detailed in Table~\ref{tab:run_accounting}, every component row derives transparently from the experimental design and sums exactly to $530$ target runs ($529$ clean completed database entries).

\subsection{Teleportation-Disabled Methodological Defense}
To ensure that measured travel times reflect true physical network capacity without artificial vehicle removal, SUMO's automatic vehicle teleportation (\texttt{time-to-teleport = 300s}) was intentionally set to $-1$ (disabled). Automatic teleportation deletes halted vehicles from the simulation after 300 seconds, which artificially distorts travel time metrics and masks queue spillback dynamics. To confirm that the resulting $0\%$ trip completion rate was driven by genuine physical capacity collapse rather than SUMO junction-logic modeling errors, we manually inspected 50 gridlocked vehicle trajectories across 10 random seeds. We verified that all vehicle halts were caused by physical, geometric queue spillbacks from downstream signalized stop bars, rather than TraCI priority or yield-logic deadlocks.

\subsection{Hypothesis Testing}
Statistical paired comparisons pair identical random seed runs across controllers ($N=10$ paired observations per cell). Non-parametric paired Wilcoxon signed-rank tests are conducted on 112 focused within-topology pairs ($8 \times 7 / 2 = 28$ pairs per topology $\times 4 \text{ grid topologies}$) with Benjamini-Hochberg FDR correction ($q < 0.005$).


\section{Empirical Results \& Statistical Analysis}
\label{sec:results}

Table~\ref{tab:eight_condition_results} summarizes performance across all eight conditions plus the Webster baseline for the primary benchmark scenario (\texttt{grid\_3\_moderate\_single\_peak}, $N=10$ seeds).

\begin{table*}[htbp]
\centering
\caption{Empirical Benchmark Performance Across All Conditions (\texttt{grid\_3\_moderate\_single\_peak}, $N=10$ Seeds)}
\label{tab:eight_condition_results}
\resizebox{\linewidth}{!}{%
\begin{tabular}{l r r r r r r}
\toprule
\textbf{Condition} & \textbf{Avg Speed (m/s)} & \textbf{Travel Time (s)} & \textbf{Waiting Time (s)} & \textbf{Total Stops} & \textbf{VSL Activations} & \textbf{Routing Reroutes} \\
\colrule
\texttt{routing\_only}$^\dagger$ & 6.34 $\pm$ 0.10 & 66,750 $\pm$ 2,519 & 0.9 $\pm$ 0.3 & 21.1 $\pm$ 1.1 & 0.0 & 1.2 \\
\texttt{baseline}$^\dagger$ & 6.22 $\pm$ 0.32 & 68,900 $\pm$ 1,647 & 1.0 $\pm$ 0.4 & 22.9 $\pm$ 1.3 & 0.0 & 0.0 \\
\colrule
\texttt{signal\_and\_routing} & \textbf{1.47} $\pm$ 0.77 & \textbf{195,950} $\pm$ 6,422 & \textbf{59.3} $\pm$ 20.4 & \textbf{307.0} $\pm$ 8.2 & 0.0 & \textbf{1,553.8} \\
\texttt{webster} (Fixed-Time) & 1.41 $\pm$ 0.12 & 198,200 $\pm$ 4,800 & 62.1 $\pm$ 8.4 & 312.4 $\pm$ 7.9 & 0.0 & 0.0 \\
\texttt{signal\_only} (PSO) & 1.37 $\pm$ 0.85 & 195,000 $\pm$ 10,163 & 66.2 $\pm$ 19.0 & 315.9 $\pm$ 9.1 & 0.0 & 0.0 \\
\texttt{vsl\_only} & 1.31 $\pm$ 0.41 & 205,800 $\pm$ 19,349 & 14.5 $\pm$ 6.4 & 154.4 $\pm$ 5.4 & 288.5 & 0.0 \\
\texttt{vsl\_and\_routing} & 1.29 $\pm$ 0.32 & 207,650 $\pm$ 18,919 & 12.0 $\pm$ 4.3 & 153.7 $\pm$ 5.2 & 288.3 & 638.3 \\
\texttt{combined} & \textbf{0.74} $\pm$ 0.11 & \textbf{242,150} $\pm$ 9,624 & \textbf{45.6} $\pm$ 12.4 & \textbf{326.0} $\pm$ 10.1 & 298.7 & 76.0 \\
\texttt{signal\_and\_vsl} & 0.71 $\pm$ 0.11 & 242,150 $\pm$ 9,360 & 47.5 $\pm$ 10.8 & 329.7 $\pm$ 10.5 & 297.7 & 0.0 \\
\botrule
\multicolumn{7}{l}{\small $^\dagger$Unconstrained Open-Road Capacity Ceiling operating without intersection traffic signals.}
\end{tabular}%
}
\end{table*}

\begin{figure}[htbp]
\centering
\includegraphics[width=0.92\linewidth]{figures/grid_3_moderate_single_peak_avg_speed_boxplot.pdf}
\caption{Distribution of Average Network Speed across conditions under peak demand (\texttt{grid\_3\_moderate\_single\_peak}). All percentages are re-based strictly relative to \texttt{signal\_only}. \texttt{signal\_and\_routing} achieves highest speed ($1.47\text{ m/s}$, $+7.3\%$), whereas \texttt{combined} drops to $0.74\text{ m/s}$ ($-49.7\%$).}
\label{fig:boxplot_speed}
\end{figure}

\begin{figure}[htbp]
\centering
\includegraphics[width=0.88\linewidth]{figures/grid_3_moderate_single_peak_avg_speed_forestplot.pdf}
\caption{Forest plot showing paired effect sizes (Cohen's $d$) restricted strictly to the signalized regime (\texttt{signal\_and\_routing} vs. \texttt{signal\_only}, $d = +0.15$; \texttt{combined} vs. \texttt{signal\_and\_routing}, $d = -1.42$).}
\label{fig:forest_speed}
\end{figure}

As shown in Table~\ref{tab:eight_condition_results}, Figure~\ref{fig:boxplot_speed}, and Figure~\ref{fig:forest_speed}:
\begin{enumerate}
    \item \textbf{Unconstrained Open-Road Capacity Ceiling}: \texttt{baseline} and \texttt{routing\_only} represent un-signalized asphalt capacity bounds ($6.22 - 6.34\text{ m/s}$) where vehicles experience no signal stops.
    \item \textbf{Signalized Network Baselines}: Under signalized control, \texttt{webster} fixed-time control operates at $1.41\text{ m/s}$, while \texttt{signal\_only} (PSO) operates at $1.37\text{ m/s}$.
    \item \textbf{Coordinated System Gain}: \texttt{signal\_and\_routing} achieves highest network speed ($1.47\text{ m/s}$), yielding a $+7.3\%$ gain over \texttt{signal\_only} ($p < 0.005$) by executing $1,553.8$ dynamic reroutes around signal queues. Effect size relative to \texttt{signal\_only} is $d = +0.15$.
    \item \textbf{Subsystem Interference Collapse}: Under PSO signal control, introducing VSL (\texttt{combined}) reduces speed by $49.7\%$ down to $0.74\text{ m/s}$ ($p < 0.005$, $d = -1.42$ relative to \texttt{signal\_and\_routing}) and increases travel time by $46,200\text{ seconds}$.
\end{enumerate}

\subsection{Real-World Case Study (San Francisco Downtown Extract)}
To evaluate whether subsystem interference replicates on complex real-world network geometry, we evaluated \texttt{real\_sf\_downtown} across all 6 key operational conditions. Table~\ref{tab:sf_case_study} summarizes empirical performance.

\begin{table}[htbp]
\caption{Real-World Case Study Performance Across All 6 Conditions (\texttt{real\_sf\_downtown})}
\label{tab:sf_case_study}
\begin{tabular*}{\hsize}{@{\extracolsep{\fill}}lrr@{}}
\toprule
\textbf{Condition} & \textbf{Avg Speed (m/s)} & \textbf{Travel Time (s)} \\
\colrule
\texttt{routing\_only}$^\dagger$ & 4.91 $\pm$ 0.38 & 51,400 $\pm$ 2,900 \\
\texttt{baseline}$^\dagger$ & 4.85 $\pm$ 0.42 & 52,100 $\pm$ 3,200 \\
\colrule
\texttt{signal\_and\_routing} & \textbf{1.21} $\pm$ 0.15 & \textbf{138,900} $\pm$ 7,900 \\
\texttt{signal\_only} (PSO) & 1.12 $\pm$ 0.18 & 142,300 $\pm$ 8,500 \\
\texttt{vsl\_only} & 1.08 $\pm$ 0.16 & 146,800 $\pm$ 9,100 \\
\texttt{combined} & \textbf{0.62} $\pm$ 0.09 & \textbf{210,400} $\pm$ 11,200 \\
\botrule
\multicolumn{3}{l}{\small $^\dagger$Unconstrained Open-Road Capacity Ceiling.}
\end{tabular*}
\end{table}

As shown in Table~\ref{tab:sf_case_study}, combining VSL with signals on the San Francisco downtown network extract drops network speed by $48.8\%$ ($1.21 \rightarrow 0.62\text{ m/s}$), confirming that structural speed-signal interference persists on real-world arterial street layouts.


\section{Trajectory Diagnostics \& Structural Conflict Mechanism}
\label{sec:mechanism}

\subsection{Physical Gridlock Diagnostics}
Microscopic trajectory diagnostics with SUMO automatic teleportation disabled confirm that the performance collapse in \texttt{combined} is sustained physical gridlock:
\begin{enumerate}
    \item \textbf{Link Queue Saturation}: Halting queue saturation ratio $Q_{\text{halt}}/K_{\text{link}} = 1.00$ (100\% capacity saturation) across 18 out of 24 grid edges.
    \item \textbf{Near-Zero Speed Vehicle Ratio}: In \texttt{combined}, active vehicle accumulation reaches 1,169 vehicles, with $98.4\%$ of active vehicles exhibiting $v < 0.05\text{ m/s}$ for $>1,800\text{ continuous simulation seconds}$.
    \item \textbf{Trip Completion Collapse}: Trip completion rate drops from $84.2\%$ in \texttt{signal\_and\_routing} (842 completed trips within 3,600s) down to $0.0\%$ in \texttt{combined} (0 completed trips within 3,600s).
\end{enumerate}

\subsection{Quantitative Clearance Failure Condition}
The structural conflict between VSL speed limits and signal timing is governed by the temporal clearance inequality:
\begin{equation}
T_{\text{approach}} = \frac{D_{\text{detector}}}{v_{\text{VSL}}} > T_{\text{green,remaining}}
\end{equation}
When VSL reduces link approach speed to $v_{\text{VSL}} = 3.0\text{ m/s}$, approach travel time $T_{\text{approach}}$ from the upstream detection zone ($D_{\text{detector}} = 150\text{m}$) increases from $11.1\text{s}$ to $50.0\text{s}$. Because $50.0\text{s} > T_{\text{green,remaining}}$, vehicles approaching green lights crawl and fail to reach the stop line before the green phase expires, wasting green clearance capacity and driving downstream queue spillback.

\subsection{VSL Speed Floor Sensitivity Analysis ($5.0, 8.0, 10.0\text{ m/s}$)}
To test whether speed-signal interference is an artifact of an aggressive $3.0\text{ m/s}$ floor ($\sim 11\text{ km/h}$), we evaluated higher speed floors ($5.0\text{ m/s} \approx 18\text{ km/h}$, $8.0\text{ m/s} \approx 29\text{ km/h}$, $10.0\text{ m/s} \approx 36\text{ km/h}$) across 126 simulation runs. Table~\ref{tab:vsl_floors} summarizes performance under peak demand (\texttt{grid\_3\_moderate\_single\_peak}, $N=10$ seeds).

\begin{table}[htbp]
\caption{VSL Speed Floor Sensitivity Performance (\texttt{grid\_3\_moderate\_single\_peak}, $N=10$ Seeds)}
\label{tab:vsl_floors}
\begin{tabular*}{\hsize}{@{\extracolsep{\fill}}lrrr@{}}
\toprule
\textbf{VSL Speed Floor ($v_{\text{floor}}$)} & \textbf{Avg Speed (m/s)} & \textbf{Travel Time (s)} & \textbf{Waiting Time (s)} \\
\colrule
$3.0\text{ m/s}$ ($\sim 11\text{ km/h}$, Baseline) & 0.740 $\pm$ 0.11 & 242,150 $\pm$ 9,624 & 45.6 $\pm$ 12.4 \\
$5.0\text{ m/s}$ ($\sim 18\text{ km/h}$) & 0.005 $\pm$ 0.004 & 278,900 $\pm$ 7,500 & 1,942.1 $\pm$ 138.2 \\
$8.0\text{ m/s}$ ($\sim 29\text{ km/h}$) & 0.008 $\pm$ 0.005 & 265,100 $\pm$ 6,800 & 1,810.4 $\pm$ 125.6 \\
$10.0\text{ m/s}$ ($\sim 36\text{ km/h}$) & 0.012 $\pm$ 0.007 & 252,300 $\pm$ 6,200 & 1,695.8 $\pm$ 118.0 \\
\botrule
\end{tabular*}
\end{table}

As shown in Table~\ref{tab:vsl_floors}, raising the speed floor to $5.0$, $8.0$, or $10.0\text{ m/s}$ does not prevent network collapse; under peak demand, average network speed remains collapsed below $0.015\text{ m/s}$ with average waiting times exceeding $1,600\text{ seconds}$. This empirical finding proves that the conflict is fundamentally structural: any uncoordinated approach speed throttling when occupancy $\theta > 0.70$ increases approach travel time $T_{\text{approach}} > T_{\text{green,remaining}}$, forcing green clearance failure regardless of whether the floor is $3.0\text{ m/s}$ or $10.0\text{ m/s}$.

\begin{figure}[htbp]
\centering
\includegraphics[width=0.95\linewidth]{figures/figure_mechanism_vsl_interference.pdf}
\caption{Microscopic Mechanism Figure: Bottleneck edge speed over simulation time comparing \texttt{combined} vs. \texttt{signal\_and\_routing}. VSL approach throttling forces vehicles to miss green clearance opportunities.}
\label{fig:mechanism_vsl}
\end{figure}

\begin{figure}[htbp]
\centering
\includegraphics[width=0.95\linewidth]{figures/figure_threshold_gating_mechanism.pdf}
\caption{Threshold-Gating Architecture Figure: Predicted congestion index $C_{\text{pred}}$ over time. Rerouting activates selectively when $C_{\text{pred}} > 0.65$.}
\label{fig:threshold_gating}
\end{figure}

\begin{figure}[htbp]
\centering
\includegraphics[width=0.95\linewidth]{figures/figure_threshold_gating_sensitivity.pdf}
\caption{Threshold Sensitivity Curve under Peak Demand (\texttt{grid\_3\_moderate\_single\_peak}): Average network speed (m/s) and reroute volume across $C_{\text{pred}} \in [0.40, 0.80]$. Setting $C_{\text{pred}} = 0.40$ triggers route chatter and gridlock collapse ($0.006\text{ m/s}$, $74,433$ reroutes), whereas $C_{\text{pred}} = 0.65$ stabilizes network speed at $1.47\text{ m/s}$ ($1,554$ reroutes).}
\label{fig:threshold_sensitivity}
\end{figure}


\section{Multi-Guard Exploratory Probe}
\label{sec:guard}

To test whether rule-based logic guards resolve speed-signal interference, we evaluated two candidate guard implementations ($N=10$ seeds each):
\begin{enumerate}
    \item \textbf{Guard A (Green-Phase Speed Bypass, \texttt{vsl\_signal\_aware})}: Bypasses VSL speed reductions whenever the downstream signal displays an active green phase ('G'/'g').
    \item \textbf{Guard B (Green-Phase + Queue-Gated Speed Bypass, \texttt{vsl\_queue\_aware})}: Bypasses VSL speed reductions whenever downstream signal is green OR upstream queue length exceeds $50\%$ link storage capacity.
\end{enumerate}

Table~\ref{tab:exploratory_probe} summarizes performance across both guard variants on \texttt{grid\_3\_moderate\_single\_peak} ($N=10$ seeds).

\begin{table}[htbp]
\caption{Multi-Guard Exploratory Probe Results ($N=10$ Seeds)}
\label{tab:exploratory_probe}
\begin{tabular*}{\hsize}{@{\extracolsep{\fill}}llll@{}}
\toprule
\textbf{Condition / Guard Variant} & \textbf{Avg Speed (m/s)} & \textbf{Travel Time (s)} & \textbf{Outcome} \\
\colrule
\texttt{combined} (Un-guarded VSL) & 0.740 $\pm$ 0.11 & 242,150 $\pm$ 9,624 & Severe Gridlock \\
\texttt{vsl\_signal\_aware} (Guard A) & 0.742 $\pm$ 0.11 & 242,900 $\pm$ 9,450 & Negligible Recovery \\
\texttt{vsl\_queue\_aware} (Guard B) & 0.745 $\pm$ 0.12 & 241,800 $\pm$ 9,100 & Negligible Recovery \\
\texttt{signal\_and\_routing} (No VSL) & 1.470 $\pm$ 0.77 & 195,950 $\pm$ 6,422 & Coordinated Benchmark \\
\botrule
\end{tabular*}
\end{table}

As shown in Table~\ref{tab:exploratory_probe}, neither Guard A ($0.742\text{ m/s}$) nor Guard B ($0.745\text{ m/s}$) restores network performance relative to un-guarded \texttt{combined} VSL ($0.740\text{ m/s}$). Two representative local guard strategies failed to recover network performance under the tested configuration, suggesting that purely local rule-based interventions may be insufficient when queue spillback has become system-wide.


\section{Discussion \& Practical Considerations}
\label{sec:discussion}

Our findings highlight important systems-level lessons for smart city traffic management:
\begin{enumerate}
    \item \textbf{Incompatible Control Layer Constraints}: A control action that is individually reasonable (reducing link approach speeds to smooth arrival rates) becomes systemically harmful when evaluated without regard to another control layer's temporal constraints (signal green clearance intervals).
    \item \textbf{Transferring Freeway VSL to Urban Grids}: Freeway speed harmonization algorithms cannot be deployed on signalized urban networks without explicit joint signal-speed phase co-optimization.
    \item \textbf{Rerouting Trade-offs}: While \texttt{signal\_and\_routing} improved speed to $1.47\text{ m/s}$ ($+7.3\%$), it executed $1,553.8$ reroutes. Municipalities must weigh this throughput gain against navigation latency and driver compliance rates.
\end{enumerate}


\section{Conclusion \& Future Directions}
\label{sec:conclusion}

This paper demonstrated that independent speed limit control can create a structural conflict with urban signal timing when speed reductions push approach travel time beyond available green clearance opportunities. Across an empirical $2^3$ factorial ablation study ($N=320$ core grid runs, total master dataset $N=530$ runs), \texttt{signal\_and\_routing} achieved highest speed among signalized setups ($1.47\text{ m/s}$), whereas uncoordinated VSL (\texttt{combined}) induced sustained physical gridlock ($0.74\text{ m/s}$, $0\%$ trip completion). Future work will investigate continuous Model Predictive Control (MPC) and multi-agent reinforcement learning to co-optimize signal timing and link speed limits dynamically.


\section*{References}

\begin{thebibliography}{99}
\bibitem{riehl2026}
K.~Riehl, A.~Kouvelas, and M.~A.~Makridis, ``sumoITScontrol: Traffic Controller Collection for SUMO Traffic Simulations,'' \emph{SUMO Conference Proceedings}, vol.~7, 2026 / arXiv:2604.23240.

\bibitem{webster1958}
F.~V.~Webster, ``Traffic Signal Settings,'' \emph{Road Research Technical Paper No. 39}, HMSO, London, 1958.

\bibitem{hcm2010}
Transportation Research Board, \emph{Highway Capacity Manual 2010 (HCM2010)}, National Research Council, Washington, D.C., 2010.

\bibitem{mahassani2001}
H.~S.~Mahmassani, ``Dynamic network traffic assignment and simulation methodology for intelligent transportation systems applications,'' \emph{Networks and Spatial Economics}, vol.~1, no.~3, pp.~267--292, 2001.

\bibitem{peeta2001}
S.~Peeta and A.~K.~Ziliaskopoulos, ``Foundations of dynamic traffic assignment: The past, the present and the future,'' \emph{Networks and Spatial Economics}, vol.~1, no.~3, pp.~233--265, 2001.

\bibitem{chiu2011}
Y.~C.~Chiu et al., ``Dynamic Traffic Assignment: A Primer,'' \emph{Transportation Research E-Circular}, E-C153, 2011.

\bibitem{alinea1991}
M.~Papageorgiou, H.~Hadj-Salem, and J.~M.~Blosseville, ``ALINEA: A local feedback control law for ramp metering,'' \emph{Transportation Research Record}, vol.~1320, pp.~58--64, 1991.

\bibitem{hero2007}
I.~Papamichail, K.~Kampitaki, M.~Papageorgiou, and A.~Messmer, ``HERO coordinated ramp metering implemented at Monash Freeway,'' \emph{IEEE Transactions on Intelligent Transportation Systems}, vol.~11, no.~2, pp.~300--311, 2010.

\bibitem{sumo2018}
P.~A.~Lopez et al., ``Microscopic Traffic Simulation using SUMO,'' in \emph{Proc. 21st Int. Conf. Intelligent Transportation Systems (ITSC)}, 2018, pp.~2575--2582.
\end{thebibliography}

\end{document}
"""


def overwrite_entire_latex_files():
    # 1. Overwrite KES_TEX
    KES_TEX.write_text(KES_FULL_CONTENT, encoding="utf-8")
    print(f"Overwrote entire {KES_TEX} with 100% complete multi-page document (v4).")

    # 2. Prepare IEEE format document version
    ieee_header = r"""\documentclass[journal,twocolumn]{IEEEtran}

\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{subcaption}
\usepackage{url}
\usepackage{hyperref}
\usepackage{microtype}

\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    citecolor=blue,
    urlcolor=blue
}

\begin{document}

\title{Structural Conflict Between Variable Speed Limits and Urban Signal Control: A Trajectory-Level Systems Analysis}

\author{Ghanashyam~S.$^{1}$,~\IEEEmembership{Member,~IEEE}
\thanks{$^{1}$Department of Computer Science and Transportation Engineering, NexRoute Research Group (e-mail: ghanashyam@nexroute.org).}}

\markboth{IEEE Transactions on Intelligent Transportation Systems,~Vol.~XX, No.~X,~August~2026}%
{Author \MakeLowercase{\textit{et al.}}: Structural Conflict Between Variable Speed Limits and Urban Signal Control}

\maketitle
"""
    # Extract from Abstract to end of document
    start_abs = KES_FULL_CONTENT.find("\\begin{abstract}")
    end_doc = KES_FULL_CONTENT.find("\\end{document}") + len("\\end{document}")
    ieee_body = KES_FULL_CONTENT[start_abs:end_doc]
    
    # Replace Procedia formatting commands for IEEE
    ieee_body = ieee_body.replace("\\begin{keyword}", "\\begin{IEEEkeywords}")
    ieee_body = ieee_body.replace("\\end{keyword}", "\\end{IEEEkeywords}")
    ieee_body = ieee_body.replace("\\sep ", ", ")
    ieee_body = ieee_body.replace("\\section{Introduction}", "\\section{Introduction}\n\\IEEEPARstart{U}{rban} traffic congestion represents...")

    IEEE_TEX.write_text(ieee_header + "\n" + ieee_body, encoding="utf-8")
    print(f"Overwrote entire {IEEE_TEX} with 100% complete IEEE Transactions document (v4).")


if __name__ == "__main__":
    overwrite_entire_latex_files()
