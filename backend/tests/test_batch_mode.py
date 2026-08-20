"""
Unit Tests for Headless Batch-Mode Simulation Runner.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.run import parse_args, run_batch_mode, main


def test_cli_parse_batch_mode_args():
    """Verify CLI argument parsing for --mode batch, --steps, and --output-dir."""
    args = parse_args(["--mode", "batch", "--steps", "500", "--output-dir", "custom_results"])
    assert args.mode == "batch"
    assert args.steps == 500
    assert args.output-dir if hasattr(args, 'output-dir') else args.output_dir == "custom_results"


@patch("backend.run.init_traffic_manager")
def test_run_batch_mode_success(mock_init_tm, tmp_path):
    """Verify batch mode success path with mocked traffic manager returns well-formed summary data."""
    # Setup mock traffic manager and metrics logger
    mock_tm = MagicMock()
    mock_tm.metrics_logger.run_id = "test_run_123"
    
    # Create fake summary JSON file
    summary_file = tmp_path / "test_run_123_summary.json"
    summary_file.write_text('{"summary_metrics": {"avg_speed": 12.5, "completed_trips": 50}}', encoding="utf-8")
    
    mock_tm.metrics_logger.json_path = summary_file
    mock_tm.metrics_logger.csv_path = tmp_path / "test_run_123_metrics.csv"
    mock_tm.routing_strategy.__class__.__name__ = "AdaptiveRoutingStrategy"
    
    mock_init_tm.return_value = mock_tm

    args = parse_args([
        "--mode", "batch",
        "--scenario", "default",
        "--seed", "42",
        "--steps", "100",
        "--output-dir", str(tmp_path)
    ])

    summary_data = run_batch_mode(args)

    mock_init_tm.assert_called_once()
    mock_tm.run_batch_simulation.assert_called_once_with(steps=100)

    assert summary_data["run_id"] == "test_run_123"
    assert summary_data["scenario"] == "default"
    assert summary_data["seed"] == 42
    assert summary_data["enabled_components"] == {"signals": True, "vsl": True, "routing": True}
    assert summary_data["final_metrics"] == {"avg_speed": 12.5, "completed_trips": 50}


@patch("backend.run.init_traffic_manager")
def test_run_batch_mode_failure_exits_nonzero(mock_init_tm):
    """Verify that batch mode catches exceptions and exits with non-zero exit code (1)."""
    mock_tm = MagicMock()
    mock_tm.run_batch_simulation.side_effect = RuntimeError("TraCI connection failed")
    mock_init_tm.return_value = mock_tm

    args = parse_args(["--mode", "batch", "--steps", "100"])

    with pytest.raises(SystemExit) as exc_info:
        run_batch_mode(args)

    assert exc_info.value.code == 1


@patch("backend.run.run_batch_mode")
def test_main_batch_mode_invokes_run_batch_mode(mock_run_batch):
    """Verify that main() in batch mode calls run_batch_mode and exits cleanly with 0."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--mode", "batch", "--scenario", "default", "--steps", "50"])

    mock_run_batch.assert_called_once()
    assert exc_info.value.code == 0
