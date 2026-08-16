import sys
import pytest
from unittest.mock import patch, MagicMock
from backend.run import parse_args, main
from backend.app.scenario_loader import ScenarioConfig


def test_parse_args_defaults():
    args = parse_args([])
    assert args.scenario == "default"
    assert args.seed is None
    assert args.headless is False
    assert args.mode == "api"


def test_parse_args_custom_values():
    args = parse_args([
        "--scenario", "test_scen",
        "--seed", "42",
        "--headless",
        "--mode", "batch"
    ])
    assert args.scenario == "test_scen"
    assert args.seed == 42
    assert args.headless is True
    assert args.mode == "batch"


def test_parse_args_invalid_mode():
    with pytest.raises(SystemExit):
        parse_args(["--mode", "invalid"])


def test_batch_mode_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--mode", "batch"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "batch mode not yet implemented" in captured.out


@patch("backend.run.init_traffic_manager")
@patch("backend.run.app.run")
def test_main_api_mode_invokes_init_traffic_manager(mock_app_run, mock_init_tm):
    main(["--scenario", "default", "--seed", "77", "--headless"])
    mock_init_tm.assert_called_once_with(
        scenario_name="default",
        seed=77,
        headless=True
    )
    mock_app_run.assert_called_once_with(debug=True)


@patch("backend.app.routes.AdvancedTrafficManager")
def test_init_traffic_manager_creates_tm_with_scenario(mock_tm_cls):
    from backend.app.routes import init_traffic_manager
    tm = init_traffic_manager(scenario_name="default", seed=42, headless=True)
    mock_tm_cls.assert_called_once()
    call_kwargs = mock_tm_cls.call_args.kwargs
    assert call_kwargs["scenario_config"].name == "default"
    assert call_kwargs["seed"] == 42
    assert call_kwargs["headless"] is True
