import csv
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from backend.app.metrics_logger import RunMetricsLogger, generate_run_id
from backend.app.traffic_manager import AdvancedTrafficManager
from backend.app.scenario_loader import load_scenario


def test_generate_run_id():
    """Verify run ID generation formats."""
    run_id1 = generate_run_id("test_scen", 42)
    assert run_id1.startswith("test_scen_seed42_")

    run_id2 = generate_run_id("default", None)
    assert run_id2.startswith("default_seedNone_")


def test_metrics_logger_csv_and_json_output(tmp_path):
    """Verify logging step metrics, flushing CSV, and writing summary JSON."""
    logger = RunMetricsLogger(
        run_id="custom_run_001",
        output_dir=tmp_path,
        scenario_name="test_scenario",
        seed=100
    )

    # Log fake steps
    step1_metrics = {
        "avg_speed": 12.5,
        "system_congestion": 0.15,
        "completed_trips": 2
    }
    step2_metrics = {
        "avg_speed": 14.0,
        "system_congestion": 0.20,
        "completed_trips": 5
    }

    logger.log_step(0.0, step1_metrics)
    logger.log_step(30.0, step2_metrics)

    # Flush first batch
    logger.flush()

    csv_file = tmp_path / "custom_run_001_timeseries.csv"
    json_file = tmp_path / "custom_run_001_summary.json"

    assert csv_file.exists()

    # Read back CSV
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert float(reader[0]["sim_time"]) == 0.0
        assert float(reader[0]["avg_speed"]) == 12.5
        assert float(reader[1]["sim_time"]) == 30.0
        assert float(reader[1]["avg_speed"]) == 14.0

    # Log a 3rd step to verify append behavior on second flush
    step3_metrics = {
        "avg_speed": 15.2,
        "system_congestion": 0.10,
        "completed_trips": 8
    }
    logger.log_step(60.0, step3_metrics)
    logger.flush()

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 3
        assert float(reader[2]["sim_time"]) == 60.0
        assert float(reader[2]["avg_speed"]) == 15.2

    # Write summary
    summary_metrics = {
        "avg_speed": 15.2,
        "system_congestion": 0.10,
        "total_trips": 8
    }
    logger.write_summary(summary_metrics)

    assert json_file.exists()
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["run_id"] == "custom_run_001"
        assert data["scenario_name"] == "test_scenario"
        assert data["seed"] == 100
        assert data["summary_metrics"]["avg_speed"] == 15.2


@patch("backend.app.traffic_manager.traci.start")
@patch("backend.app.traffic_manager.sumolib.net.readNet")
@patch("backend.app.traffic_manager.sumolib.checkBinary", return_value="sumo")
def test_traffic_manager_integration_with_metrics_logger(mock_check_binary, mock_read_net, mock_traci_start, tmp_path):
    """Verify AdvancedTrafficManager initializes RunMetricsLogger with output_dir and run_id."""
    scen_cfg = load_scenario("default")

    tm = AdvancedTrafficManager(
        scenario_config=scen_cfg,
        seed=42,
        headless=True,
        output_dir=tmp_path,
        run_id="integration_run_test"
    )

    assert tm.metrics_logger.run_id == "integration_run_test"
    assert tm.metrics_logger.output_dir == tmp_path
