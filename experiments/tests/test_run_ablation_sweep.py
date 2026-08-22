"""
Unit tests for Ablation Experiment Matrix Sweep Orchestrator.
Mocks subprocess invocation to verify flag construction, resumability, and error handling.
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add repository root to sys.path so 'experiments' package is importable
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from experiments.run_ablation_sweep import (
    build_run_command,
    load_completed_manifest_entries,
    run_ablation_sweep,
    ABLATION_CONDITIONS
)


def test_ablation_condition_definitions():
    """Verify that all 5 required research conditions are defined with exact parameters."""
    expected_conditions = ["baseline", "signal_only", "vsl_only", "routing_only", "combined"]
    assert sorted(list(ABLATION_CONDITIONS.keys())) == sorted(expected_conditions)

    # 1. baseline
    b = ABLATION_CONDITIONS["baseline"]
    assert b["enable_signals"] is False
    assert b["enable_vsl"] is False
    assert b["enable_routing"] is False

    # 2. signal_only (strategy=pso)
    s = ABLATION_CONDITIONS["signal_only"]
    assert s["enable_signals"] is True
    assert s["signal_strategy"] == "pso"
    assert s["enable_vsl"] is False
    assert s["enable_routing"] is False

    # 3. vsl_only
    v = ABLATION_CONDITIONS["vsl_only"]
    assert v["enable_signals"] is False
    assert v["enable_vsl"] is True
    assert v["enable_routing"] is False

    # 4. routing_only (strategy=adaptive)
    r = ABLATION_CONDITIONS["routing_only"]
    assert r["enable_signals"] is False
    assert r["enable_vsl"] is False
    assert r["enable_routing"] is True
    assert r["routing_strategy"] == "adaptive"

    # 5. combined
    c = ABLATION_CONDITIONS["combined"]
    assert c["enable_signals"] is True
    assert c["signal_strategy"] == "pso"
    assert c["enable_vsl"] is True
    assert c["enable_routing"] is True
    assert c["routing_strategy"] == "adaptive"


def test_flag_construction_for_all_conditions():
    """Verify build_run_command constructs exact required CLI flags for each of the 5 named conditions."""
    # 1. baseline
    cmd_base = build_run_command("grid_3_light", 42, "baseline", steps=100)
    assert "--no-enable-signals" in cmd_base
    assert "--no-enable-vsl" in cmd_base
    assert "--no-enable-routing" in cmd_base
    assert "--signal-strategy" in cmd_base and cmd_base[cmd_base.index("--signal-strategy") + 1] == "webster"
    assert "--routing-strategy" in cmd_base and cmd_base[cmd_base.index("--routing-strategy") + 1] == "static"

    # 2. signal_only (must set --signal-strategy pso and --enable-signals)
    cmd_sig = build_run_command("grid_3_light", 42, "signal_only", steps=100)
    assert "--enable-signals" in cmd_sig
    assert "--no-enable-vsl" in cmd_sig
    assert "--no-enable-routing" in cmd_sig
    assert "--signal-strategy" in cmd_sig and cmd_sig[cmd_sig.index("--signal-strategy") + 1] == "pso"
    assert "--routing-strategy" in cmd_sig and cmd_sig[cmd_sig.index("--routing-strategy") + 1] == "static"

    # 3. vsl_only
    cmd_vsl = build_run_command("grid_3_light", 42, "vsl_only", steps=100)
    assert "--no-enable-signals" in cmd_vsl
    assert "--enable-vsl" in cmd_vsl
    assert "--no-enable-routing" in cmd_vsl

    # 4. routing_only (must set --routing-strategy adaptive and --enable-routing)
    cmd_route = build_run_command("grid_3_light", 42, "routing_only", steps=100)
    assert "--no-enable-signals" in cmd_route
    assert "--no-enable-vsl" in cmd_route
    assert "--enable-routing" in cmd_route
    assert "--routing-strategy" in cmd_route and cmd_route[cmd_route.index("--routing-strategy") + 1] == "adaptive"

    # 5. combined
    cmd_comb = build_run_command("grid_3_light", 42, "combined", steps=100)
    assert "--enable-signals" in cmd_comb
    assert "--signal-strategy" in cmd_comb and cmd_comb[cmd_comb.index("--signal-strategy") + 1] == "pso"
    assert "--enable-vsl" in cmd_comb
    assert "--enable-routing" in cmd_comb
    assert "--routing-strategy" in cmd_comb and cmd_comb[cmd_comb.index("--routing-strategy") + 1] == "adaptive"


def test_resumability_logic(tmp_path):
    """Verify that existing successful entries in sweep_manifest.jsonl are skipped on re-execution."""
    manifest_file = tmp_path / "sweep_manifest.jsonl"
    
    # Pre-seed manifest with successful entry for (grid_3_light, seed=1, condition='signal_only')
    existing_record = {
        "scenario": "grid_3_light",
        "seed": 1,
        "condition": "signal_only",
        "exit_code": 0,
        "summary": {"avg_speed": 10.5}
    }
    manifest_file.write_text(json.dumps(existing_record) + "\n", encoding="utf-8")

    # Verify load_completed_manifest_entries reads the pre-seeded record
    completed = load_completed_manifest_entries(manifest_file)
    assert ("grid_3_light", 1, "signal_only") in completed

    # Mock subprocess.run
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = '{"run_id": "test", "final_metrics": {}}\n'
    mock_run.return_value.stderr = ""

    with patch("subprocess.run", mock_run):
        res = run_ablation_sweep(
            scenarios=["grid_3_light"],
            seeds=[1],
            conditions=["signal_only", "combined"],
            steps=10,
            output_dir=tmp_path
        )

    # (grid_3_light, 1, signal_only) was skipped; only (grid_3_light, 1, combined) ran
    assert res["skipped"] == 1
    assert res["succeeded"] == 1
    assert mock_run.call_count == 1

    # Verify command launched was for 'combined'
    launched_cmd = mock_run.call_args[0][0]
    assert "combined" in launched_cmd or "--enable-routing" in launched_cmd


def test_subprocess_failure_recording(tmp_path):
    """Verify that a subprocess failure (nonzero exit code) is recorded in manifest rather than crashing the sweep."""
    mock_run = MagicMock()
    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = "Error: TraCI connection failed"

    with patch("subprocess.run", mock_run):
        res = run_ablation_sweep(
            scenarios=["grid_3_light"],
            seeds=[42],
            conditions=["baseline"],
            steps=10,
            output_dir=tmp_path
        )

    assert res["failed"] == 1
    assert res["succeeded"] == 0

    manifest_file = tmp_path / "sweep_manifest.jsonl"
    assert manifest_file.exists()

    with open(manifest_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        record = json.loads(lines[0])

    assert record["scenario"] == "grid_3_light"
    assert record["seed"] == 42
    assert record["condition"] == "baseline"
    assert record["exit_code"] == 1
    assert "Error: TraCI connection failed" in record["error"]
