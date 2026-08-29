"""
NexRoute Top-Level Ablation Experiment Sweep Orchestrator.

Runs the full ablation experiment matrix across scenarios, seeds, and the 5 specific research conditions:
  1. baseline      (no signals, no VSL, no dynamic routing)
  2. signal_only   (PSO traffic signals enabled, no VSL, no dynamic routing)
  3. vsl_only      (VSL enabled, no signals, no dynamic routing)
  4. routing_only  (Adaptive PSO routing enabled, no signals, no VSL)
  5. combined      (PSO signals, VSL, and adaptive PSO routing all enabled)

Invokes backend/run.py in batch mode for each cell, captures stdout JSON metrics,
writes consolidated records to sweep_manifest.jsonl, and supports crash-safe resumability.
"""

import sys
import os
import time
import json
import argparse
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Named Ablation Conditions Mapping (Project Research Questions)
# Do not alter condition names or parameter combinations.
ABLATION_CONDITIONS: Dict[str, Dict[str, Any]] = {
    "baseline": {
        "enable_signals": False,
        "signal_strategy": "webster",
        "enable_vsl": False,
        "enable_routing": False,
        "routing_strategy": "static"
    },
    "signal_only": {
        "enable_signals": True,
        "signal_strategy": "pso",
        "enable_vsl": False,
        "enable_routing": False,
        "routing_strategy": "static"
    },
    "vsl_only": {
        "enable_signals": False,
        "signal_strategy": "webster",
        "enable_vsl": True,
        "enable_routing": False,
        "routing_strategy": "static"
    },
    "routing_only": {
        "enable_signals": False,
        "signal_strategy": "webster",
        "enable_vsl": False,
        "enable_routing": True,
        "routing_strategy": "adaptive"
    },
    "signal_and_routing": {
        "enable_signals": True,
        "signal_strategy": "pso",
        "enable_vsl": False,
        "enable_routing": True,
        "routing_strategy": "adaptive"
    },
    "combined": {
        "enable_signals": True,
        "signal_strategy": "pso",
        "enable_vsl": True,
        "enable_routing": True,
        "routing_strategy": "adaptive"
    }
}


def build_run_command(
    scenario: str,
    seed: int,
    condition_name: str,
    steps: int = 500,
    output_dir: Path = None,
    repo_root: Path = None
) -> List[str]:
    """
    Construct the command line argument list for invoking backend/run.py in batch mode
    for a specific (scenario, seed, condition) combination.
    """
    if condition_name not in ABLATION_CONDITIONS:
        raise ValueError(f"Unknown condition '{condition_name}'. Must be one of {list(ABLATION_CONDITIONS.keys())}")

    cfg = ABLATION_CONDITIONS[condition_name]
    
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    run_py = repo_root / "backend" / "run.py"
    
    cmd = [
        sys.executable,
        str(run_py),
        "--mode", "batch",
        "--scenario", scenario,
        "--seed", str(seed),
        "--headless",
        "--steps", str(steps),
        "--signal-strategy", cfg["signal_strategy"],
        "--routing-strategy", cfg["routing_strategy"]
    ]
    
    # Subsystem toggle flags using argparse.BooleanOptionalAction format
    if cfg["enable_signals"]:
        cmd.append("--enable-signals")
    else:
        cmd.append("--no-enable-signals")

    if cfg["enable_vsl"]:
        cmd.append("--enable-vsl")
    else:
        cmd.append("--no-enable-vsl")

    if cfg["enable_routing"]:
        cmd.append("--enable-routing")
    else:
        cmd.append("--no-enable-routing")

    if output_dir is not None:
        cmd.extend(["--output-dir", str(output_dir)])

    return cmd


def load_completed_manifest_entries(manifest_path: Path) -> Set[Tuple[str, int, str]]:
    """
    Parse existing sweep_manifest.jsonl file to identify (scenario, seed, condition)
    cells that have already completed successfully.
    """
    completed = set()
    if not manifest_path.exists():
        return completed

    with open(manifest_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                scenario = entry.get("scenario")
                seed = entry.get("seed")
                condition = entry.get("condition")
                exit_code = entry.get("exit_code")

                # Mark as completed if run exited cleanly with exit_code == 0
                if scenario and seed is not None and condition and exit_code == 0:
                    completed.add((scenario, int(seed), condition))
            except json.JSONDecodeError:
                logger.warning(f"Malformed JSON on line {line_num} in manifest file '{manifest_path}'")

    return completed


def execute_single_cell(
    scenario: str,
    seed: int,
    condition: str,
    steps: int,
    output_dir: Path,
    repo_root: Path
) -> Dict[str, Any]:
    """Execute a single simulation run via subprocess and parse stdout JSON output."""
    cmd = build_run_command(scenario, seed, condition, steps, output_dir, repo_root)
    
    start_time = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    duration_sec = time.time() - start_time
    
    result_record = {
        "scenario": scenario,
        "seed": seed,
        "condition": condition,
        "exit_code": res.returncode,
        "duration_seconds": round(duration_sec, 2),
        "cmd": cmd
    }
    
    if res.returncode == 0:
        # Parse final JSON summary line from stdout
        stdout_lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        summary_json = None
        for line in reversed(stdout_lines):
            if line.startswith("{") and line.endswith("}"):
                try:
                    summary_json = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        if summary_json:
            result_record["summary"] = summary_json
        else:
            result_record["raw_stdout"] = res.stdout[-1000:]
    else:
        result_record["error"] = f"Subprocess exited with code {res.returncode}:\n{res.stderr[-1000:]}"
        
    return result_record


def run_ablation_sweep(
    scenarios: List[str],
    seeds: List[int],
    conditions: List[str] = None,
    steps: int = 500,
    output_dir: Path = None,
    parallel: int = 1,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Run full ablation experiment matrix over scenarios x seeds x conditions.
    
    Note: Parallel execution (--parallel N) runs up to N SUMO subprocesses concurrently.
    Each SUMO simulation instance consumes significant CPU & RAM resources. Ensure your machine
    has adequate hardware capacity before increasing N > 1.
    """
    repo_root = Path(__file__).resolve().parent.parent
    if output_dir is None:
        output_dir = repo_root / "experiments" / "results"
    else:
        output_dir = Path(output_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "sweep_manifest.jsonl"

    if conditions is None:
        conditions = list(ABLATION_CONDITIONS.keys())

    # Load existing successful entries for resumability
    completed_cells = load_completed_manifest_entries(manifest_path)
    
    manifest_lock = threading.Lock()

    # Build work queue of all (scenario, seed, condition) combinations
    all_cells = [
        (sc, sd, cond)
        for sc in scenarios
        for sd in seeds
        for cond in conditions
    ]

    pending_cells = [
        cell for cell in all_cells
        if cell not in completed_cells
    ]

    total_attempted = len(all_cells)
    skipped_count = total_attempted - len(pending_cells)
    succeeded_count = 0
    failed_count = 0

    logger.info(
        f"Starting Ablation Sweep: {total_attempted} total cells "
        f"({len(scenarios)} scenarios x {len(seeds)} seeds x {len(conditions)} conditions). "
        f"Resuming: {skipped_count} skipped, {len(pending_cells)} pending."
    )

    if dry_run:
        print("\n" + "=" * 70)
        print(" [DRY RUN MODE] - Simulation Subprocesses Will NOT Be Launched")
        print("=" * 70)
        print(f"Scenarios ({len(scenarios)}): {', '.join(scenarios)}")
        print(f"Seeds ({len(seeds)}):     {seeds}")
        print(f"Conditions ({len(conditions)}): {', '.join(conditions)}")
        print(f"Total Runs:       {total_attempted}")
        print(f"Pending Runs:     {len(pending_cells)}")
        print("=" * 70 + "\n")
        return {
            "total": total_attempted,
            "skipped": skipped_count,
            "succeeded": 0,
            "failed": 0,
            "duration_sec": 0.0,
            "manifest": str(manifest_path)
        }

    sweep_start_time = time.time()

    def process_cell(cell: Tuple[str, int, str]) -> Dict[str, Any]:
        sc, sd, cond = cell
        logger.info(f"Executing cell: scenario='{sc}', seed={sd}, condition='{cond}'")
        res = execute_single_cell(sc, sd, cond, steps, output_dir, repo_root)

        # Thread-safe append to manifest file
        with manifest_lock:
            with open(manifest_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(res) + "\n")
                f.flush()

        return res

    if parallel > 1:
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            future_to_cell = {executor.submit(process_cell, cell): cell for cell in pending_cells}
            for future in as_completed(future_to_cell):
                try:
                    res = future.result()
                    if res.get("exit_code") == 0:
                        succeeded_count += 1
                    else:
                        failed_count += 1
                except Exception as exc:
                    failed_count += 1
                    logger.error(f"Execution failed with exception: {exc}")
    else:
        for cell in pending_cells:
            res = process_cell(cell)
            if res.get("exit_code") == 0:
                succeeded_count += 1
            else:
                failed_count += 1

    total_wall_time = time.time() - sweep_start_time

    # Print final summary report table
    print("\n" + "=" * 70)
    print("Ablation Sweep Execution Summary")
    print("=" * 70)
    print(f"Total Combinations Configured: {total_attempted:6d}")
    print(f"Skipped (Already Resumed):     {skipped_count:6d}")
    print(f"Executed & Succeeded:          {succeeded_count:6d}")
    print(f"Executed & Failed:             {failed_count:6d}")
    print(f"Total Wall-Clock Time:         {total_wall_time:6.2f}s")
    print("=" * 70 + "\n")

    return {
        "total": total_attempted,
        "skipped": skipped_count,
        "succeeded": succeeded_count,
        "failed": failed_count,
        "duration_sec": total_wall_time,
        "manifest": str(manifest_path)
    }


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Run NexRoute Full Ablation Experiment Matrix Sweep Orchestrator"
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        required=True,
        help="Comma-separated list of scenario names (e.g. 'grid_3_light,grid_5_moderate')"
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="1,2,3,4,5",
        help="Comma-separated list of integer random seeds (default: '1,2,3,4,5')"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=500,
        help="Simulation duration steps per run cell (default: 500)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Target output directory for sweep manifest and metrics (default: 'experiments/results/')"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of concurrent subprocesses (default: 1 sequential run)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned sweep execution matrix without launching simulation subprocesses"
    )
    return parser.parse_args(args)


def main(args=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parsed = parse_args(args)

    scenario_list = [s.strip() for s in parsed.scenarios.split(",") if s.strip()]
    seed_list = [int(s.strip()) for s in parsed.seeds.split(",") if s.strip()]

    run_ablation_sweep(
        scenarios=scenario_list,
        seeds=seed_list,
        steps=parsed.steps,
        output_dir=Path(parsed.output_dir) if parsed.output_dir else None,
        parallel=parsed.parallel,
        dry_run=parsed.dry_run
    )


if __name__ == "__main__":
    main()
