from pathlib import Path
from click.testing import CliRunner

from terminal_dashboard.app import DashboardApp
from terminal_dashboard.cli import main
from terminal_dashboard.models import DashboardConfig


def test_cli_snapshot():
    runner = CliRunner()
    result = runner.invoke(main, ["snapshot"])
    assert result.exit_code == 0
    assert "TERMINAL DASHBOARD" in result.output
    assert "CPU Telemetry" in result.output
    assert "Memory & Swap" in result.output


def test_cli_cpu():
    runner = CliRunner()
    result = runner.invoke(main, ["cpu"])
    assert result.exit_code == 0
    assert "CPU Telemetry" in result.output


def test_cli_mem():
    runner = CliRunner()
    result = runner.invoke(main, ["mem"])
    assert result.exit_code == 0
    assert "Memory & Swap" in result.output


def test_cli_disk():
    runner = CliRunner()
    result = runner.invoke(main, ["disk"])
    assert result.exit_code == 0
    assert "Storage & Disks" in result.output


def test_cli_net():
    runner = CliRunner()
    result = runner.invoke(main, ["net"])
    assert result.exit_code == 0
    assert "Network Telemetry" in result.output


def test_cli_proc():
    runner = CliRunner()
    result = runner.invoke(main, ["proc", "--limit", "5"])
    assert result.exit_code == 0
    assert "Top Processes" in result.output


def test_cli_proc_search():
    runner = CliRunner()
    result = runner.invoke(main, ["proc", "--search", "python", "--limit", "5"])
    assert result.exit_code == 0
    assert "Top Processes" in result.output


def test_cli_check():
    runner = CliRunner()
    result = runner.invoke(main, ["check"])
    assert result.exit_code in (0, 1, 2)
    assert any(status in result.output for status in ("HEALTHY", "WARNING", "CRITICAL"))


def test_cli_export(tmp_path: Path):
    target = tmp_path / "out.json"
    runner = CliRunner()
    result = runner.invoke(main, ["export", "--format", "json", "--output", str(target)])
    assert result.exit_code == 0
    assert target.exists()


def test_cli_config_show():
    runner = CliRunner()
    result = runner.invoke(main, ["config-show"])
    assert result.exit_code == 0
    assert "refresh_interval" in result.output


def test_cli_config_init(tmp_path: Path):
    target = tmp_path / "init_cfg.json"
    runner = CliRunner()
    result = runner.invoke(main, ["config-init", "--path", str(target)])
    assert result.exit_code == 0
    assert target.exists()


def test_dashboard_app_step():
    cfg = DashboardConfig(refresh_interval=0.5, history_points=10)
    app = DashboardApp(config=cfg)
    layout = app.step()
    assert layout is not None
    assert len(app.cpu_history) == 1
    assert len(app.mem_history) == 1


def test_dashboard_app_run_fixed_iterations():
    cfg = DashboardConfig(refresh_interval=0.01)
    app = DashboardApp(config=cfg)
    app.run(max_iterations=2)
    assert len(app.cpu_history) >= 1
