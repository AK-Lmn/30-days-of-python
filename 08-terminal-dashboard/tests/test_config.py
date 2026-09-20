from pathlib import Path
import json

from terminal_dashboard.config import load_config, parse_config_dict, save_config
from terminal_dashboard.models import DashboardConfig


def test_load_default_config(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist.json"
    cfg = load_config(non_existent)
    assert cfg.refresh_interval == 1.0
    assert cfg.history_points == 30


def test_parse_config_dict():
    data = {
        "refresh_interval": 2.5,
        "history_points": 50,
        "cpu_warning_threshold": 65.0,
        "process_sort_by": "mem",
    }
    cfg = parse_config_dict(data)
    assert cfg.refresh_interval == 2.5
    assert cfg.history_points == 50
    assert cfg.cpu_warning_threshold == 65.0
    assert cfg.process_sort_by == "mem"


def test_save_and_load_config(tmp_path: Path):
    target = tmp_path / "custom_config.json"
    cfg = DashboardConfig(refresh_interval=3.0, history_points=45, process_limit=25)
    written = save_config(cfg, target)
    assert written == target
    assert target.exists()

    loaded = load_config(target)
    assert loaded.refresh_interval == 3.0
    assert loaded.history_points == 45
    assert loaded.process_limit == 25
