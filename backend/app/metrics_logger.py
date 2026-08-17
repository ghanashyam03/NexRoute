import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

logger = logging.getLogger(__name__)


def generate_run_id(scenario_name: str = "default", seed: Optional[int] = None) -> str:
    """Generate a run ID matching '{scenario_name}_seed{seed}_{timestamp}' format."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    seed_str = f"seed{seed}" if seed is not None else "seedNone"
    return f"{scenario_name}_{seed_str}_{timestamp}"


class RunMetricsLogger:
    """
    Logger that persists simulation step metrics (time-series CSV)
    and run summaries (summary JSON) to disk.
    """
    def __init__(
        self,
        run_id: Optional[str] = None,
        output_dir: Optional[Union[str, Path]] = None,
        scenario_name: str = "default",
        seed: Optional[int] = None
    ):
        self.scenario_name = scenario_name
        self.seed = seed
        self.run_id = run_id if run_id else generate_run_id(scenario_name, seed)

        if output_dir is None:
            # Default to top-level results/ directory
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.output_dir = base_dir / "results"
        else:
            self.output_dir = Path(output_dir).resolve()

        self.buffer: List[Dict[str, Any]] = []
        self.csv_path = self.output_dir / f"{self.run_id}_timeseries.csv"
        self.json_path = self.output_dir / f"{self.run_id}_summary.json"

    def log_step(self, sim_time: float, metrics: Dict[str, Any]) -> None:
        """Append one row (sim_time + all metric keys/values) to the in-memory buffer."""
        row: Dict[str, Any] = {"sim_time": sim_time}
        for key, val in metrics.items():
            if hasattr(val, "item"):
                val = val.item()
            row[key] = val

        self.buffer.append(row)

    def flush(self) -> None:
        """
        Write buffered rows to {output_dir}/{run_id}_timeseries.csv.
        Creates output_dir if missing; appends if file already exists mid-run.
        Clears buffer after flushing.
        """
        if not self.buffer:
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_exists = self.csv_path.exists() and self.csv_path.stat().st_size > 0

        # Collect fieldnames with sim_time first
        fieldnames = ["sim_time"]
        for row in self.buffer:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for row in self.buffer:
                writer.writerow(row)

        self.buffer.clear()
        logger.debug(f"Flushed metrics buffer to {self.csv_path}")

    def write_summary(self, summary: Dict[str, Any]) -> None:
        """Write single-row summary (final metrics + run metadata) to {output_dir}/{run_id}_summary.json."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        clean_summary = {}
        for key, val in summary.items():
            if hasattr(val, "item"):
                val = val.item()
            clean_summary[key] = val

        summary_data = {
            "run_id": self.run_id,
            "scenario_name": self.scenario_name,
            "seed": self.seed,
            "timestamp": datetime.now().isoformat(),
            "summary_metrics": clean_summary
        }

        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        logger.info(f"Wrote summary metrics to {self.json_path}")
