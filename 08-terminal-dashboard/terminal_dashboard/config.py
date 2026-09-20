import json
from pathlib import Path
from typing import Any

from terminal_dashboard.models import DashboardConfig

DEFAULT_CONFIG_PATH = Path.home() / ".termdash.json"


def load_config(config_path: Path | str | None = None) -> DashboardConfig:
    target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not target_path.exists() or not target_path.is_file():
        return DashboardConfig()

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return parse_config_dict(data)
    except Exception:
        return DashboardConfig()


def parse_config_dict(data: dict[str, Any]) -> DashboardConfig:
    defaults = DashboardConfig()
    return DashboardConfig(
        refresh_interval=float(data.get("refresh_interval", defaults.refresh_interval)),
        history_points=int(data.get("history_points", defaults.history_points)),
        process_limit=int(data.get("process_limit", defaults.process_limit)),
        process_sort_by=str(data.get("process_sort_by", defaults.process_sort_by)),
        cpu_warning_threshold=float(data.get("cpu_warning_threshold", defaults.cpu_warning_threshold)),
        cpu_critical_threshold=float(data.get("cpu_critical_threshold", defaults.cpu_critical_threshold)),
        memory_warning_threshold=float(data.get("memory_warning_threshold", defaults.memory_warning_threshold)),
        memory_critical_threshold=float(data.get("memory_critical_threshold", defaults.memory_critical_threshold)),
        swap_warning_threshold=float(data.get("swap_warning_threshold", defaults.swap_warning_threshold)),
        swap_critical_threshold=float(data.get("swap_critical_threshold", defaults.swap_critical_threshold)),
        disk_warning_threshold=float(data.get("disk_warning_threshold", defaults.disk_warning_threshold)),
        disk_critical_threshold=float(data.get("disk_critical_threshold", defaults.disk_critical_threshold)),
    )


def save_config(config: DashboardConfig, config_path: Path | str | None = None) -> Path:
    target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)
    return target_path
