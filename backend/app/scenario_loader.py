import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union
from . import config


@dataclass
class ScenarioConfig:
    name: str
    sumo_config: Dict[str, Any]
    config_file: str
    net_file: str
    route_file: str
    gui: bool = True
    signal_strategy: str = "pso"
    routing_strategy: str = "adaptive"
    enable_signals: bool = True
    enable_vsl: bool = True
    enable_routing: bool = True
    OPTIMIZATION_INTERVAL: int = config.OPTIMIZATION_INTERVAL
    CONGESTION_THRESHOLDS: Dict[str, float] = field(default_factory=lambda: dict(config.CONGESTION_THRESHOLDS))
    SPEED_LIMITS: Dict[str, float] = field(default_factory=lambda: dict(config.SPEED_LIMITS))
    PCU_VALUES: Dict[str, float] = field(default_factory=lambda: dict(config.PCU_VALUES))
    PRIORITY_WEIGHTS: Dict[str, float] = field(default_factory=lambda: dict(config.PRIORITY_WEIGHTS))
    MAX_REROUTE_ATTEMPTS: int = config.MAX_REROUTE_ATTEMPTS
    MIN_REROUTE_INTERVAL: int = config.MIN_REROUTE_INTERVAL
    CONGESTION_HISTORY_SIZE: int = config.CONGESTION_HISTORY_SIZE
    ADAPTIVE_ROUTING_THRESHOLD: float = config.ADAPTIVE_ROUTING_THRESHOLD
    MIN_GREEN_TIME: int = config.MIN_GREEN_TIME
    MAX_GREEN_TIME: int = config.MAX_GREEN_TIME
    YELLOW_TIME: int = config.YELLOW_TIME
    ALL_RED_TIME: int = config.ALL_RED_TIME
    PSO_PARTICLES: int = config.PSO_PARTICLES
    PSO_ITERATIONS: int = config.PSO_ITERATIONS

    @property
    def config_file_path(self) -> str:
        return self.config_file

    @property
    def net_file_path(self) -> str:
        return self.net_file

    @property
    def route_file_path(self) -> str:
        return self.route_file

    @property
    def optimization_interval(self) -> int:
        return self.OPTIMIZATION_INTERVAL

    @property
    def congestion_thresholds(self) -> Dict[str, float]:
        return self.CONGESTION_THRESHOLDS

    @property
    def speed_limits(self) -> Dict[str, float]:
        return self.SPEED_LIMITS

    @property
    def pcu_values(self) -> Dict[str, float]:
        return self.PCU_VALUES

    @property
    def priority_weights(self) -> Dict[str, float]:
        return self.PRIORITY_WEIGHTS

    @property
    def max_reroute_attempts(self) -> int:
        return self.MAX_REROUTE_ATTEMPTS

    @property
    def min_reroute_interval(self) -> int:
        return self.MIN_REROUTE_INTERVAL

    @property
    def congestion_history_size(self) -> int:
        return self.CONGESTION_HISTORY_SIZE

    @property
    def adaptive_routing_threshold(self) -> float:
        return self.ADAPTIVE_ROUTING_THRESHOLD

    @property
    def min_green_time(self) -> int:
        return self.MIN_GREEN_TIME

    @property
    def max_green_time(self) -> int:
        return self.MAX_GREEN_TIME

    @property
    def yellow_time(self) -> int:
        return self.YELLOW_TIME

    @property
    def all_red_time(self) -> int:
        return self.ALL_RED_TIME

    @property
    def pso_particles(self) -> int:
        return self.PSO_PARTICLES

    @property
    def pso_iterations(self) -> int:
        return self.PSO_ITERATIONS


def _deep_merge(default_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge override_dict on top of default_dict."""
    result = dict(default_dict)
    for key, val in override_dict.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_scenario(
    scenario_name: str,
    scenarios_dir: Optional[Union[str, Path]] = None
) -> ScenarioConfig:
    """
    Load a scenario by name from scenarios_dir (defaults to backend/scenarios/).
    Resolves relative path declarations to absolute paths and applies scenario-specific overrides.
    """
    if scenarios_dir is None:
        base_dir = Path(__file__).resolve().parent.parent / "scenarios"
    else:
        base_dir = Path(scenarios_dir).resolve()

    scenario_dir = base_dir / scenario_name
    scenario_path = scenario_dir / "scenario.yaml"
    if not scenario_path.exists():
        scenario_path = scenario_dir / "scenario.yml"

    if not scenario_path.exists():
        raise FileNotFoundError(
            f"Scenario '{scenario_name}' not found at {scenario_dir}"
        )

    try:
        with open(scenario_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as err:
        raise ValueError(f"Malformed YAML in scenario file '{scenario_path}': {err}")

    if not isinstance(data, dict):
        raise ValueError(f"Invalid scenario definition in '{scenario_path}': expected a dictionary/mapping.")

    # Default parameters mapping
    params = {
        "OPTIMIZATION_INTERVAL": config.OPTIMIZATION_INTERVAL,
        "CONGESTION_THRESHOLDS": dict(config.CONGESTION_THRESHOLDS),
        "SPEED_LIMITS": dict(config.SPEED_LIMITS),
        "PCU_VALUES": dict(config.PCU_VALUES),
        "PRIORITY_WEIGHTS": dict(config.PRIORITY_WEIGHTS),
        "MAX_REROUTE_ATTEMPTS": config.MAX_REROUTE_ATTEMPTS,
        "MIN_REROUTE_INTERVAL": config.MIN_REROUTE_INTERVAL,
        "CONGESTION_HISTORY_SIZE": config.CONGESTION_HISTORY_SIZE,
        "ADAPTIVE_ROUTING_THRESHOLD": config.ADAPTIVE_ROUTING_THRESHOLD,
        "MIN_GREEN_TIME": config.MIN_GREEN_TIME,
        "MAX_GREEN_TIME": config.MAX_GREEN_TIME,
        "YELLOW_TIME": config.YELLOW_TIME,
        "ALL_RED_TIME": config.ALL_RED_TIME,
        "PSO_PARTICLES": config.PSO_PARTICLES,
        "PSO_ITERATIONS": config.PSO_ITERATIONS,
    }

    # Map supported lowercase and uppercase parameter keys
    key_map = {k.lower(): k for k in params.keys()}
    allowed_keys = {
        "name", "sumo", "signal_strategy", "routing_strategy",
        "enable_signals", "enable_vsl", "enable_routing"
    }.union(key_map.keys()).union(params.keys())

    # Validate unknown keys
    unknown_keys = [k for k in data.keys() if k not in allowed_keys and k.lower() not in key_map]
    if unknown_keys:
        raise ValueError(
            f"Unknown key(s) {unknown_keys} in scenario '{scenario_name}'. Allowed keys: {sorted(list(allowed_keys))}"
        )

    # SUMO files resolution
    sumo_data = data.get("sumo", {})
    if not isinstance(sumo_data, dict):
        raise ValueError(f"Invalid 'sumo' section in scenario '{scenario_name}': expected dictionary.")

    gui = sumo_data.get("gui", True)
    signal_strategy = data.get("signal_strategy", "pso")
    routing_strategy = data.get("routing_strategy", "adaptive")
    enable_signals = data.get("enable_signals", True)
    enable_vsl = data.get("enable_vsl", True)
    enable_routing = data.get("enable_routing", True)

    config_file_rel = sumo_data.get("config_file", "")
    net_file_rel = sumo_data.get("net_file", "")
    route_file_rel = sumo_data.get("route_file", "")

    config_file_abs = str((scenario_dir / config_file_rel).resolve()) if config_file_rel else ""
    net_file_abs = str((scenario_dir / net_file_rel).resolve()) if net_file_rel else ""
    route_file_abs = str((scenario_dir / route_file_rel).resolve()) if route_file_rel else ""

    sumo_config = {
        "gui": gui,
        "config_file": config_file_abs,
        "net_file": net_file_abs,
        "route_file": route_file_abs,
    }

    for yaml_key, yaml_val in data.items():
        if yaml_key in ("name", "sumo", "signal_strategy", "routing_strategy", "enable_signals", "enable_vsl", "enable_routing"):
            continue
        param_name = key_map.get(yaml_key.lower())
        if param_name and param_name in params:
            if isinstance(params[param_name], dict) and isinstance(yaml_val, dict):
                params[param_name] = _deep_merge(params[param_name], yaml_val)
            else:
                params[param_name] = yaml_val

    return ScenarioConfig(
        name=data.get("name", scenario_name),
        sumo_config=sumo_config,
        config_file=config_file_abs,
        net_file=net_file_abs,
        route_file=route_file_abs,
        gui=gui,
        signal_strategy=signal_strategy,
        routing_strategy=routing_strategy,
        enable_signals=enable_signals,
        enable_vsl=enable_vsl,
        enable_routing=enable_routing,
        **params
    )
