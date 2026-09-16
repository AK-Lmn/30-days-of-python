from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import httpx
import pytest
from website_monitor.cli import main
from website_monitor.db import init_db


@pytest.fixture
def runner_with_db(tmp_path: Path):
    db_file = tmp_path / "cli_test.db"
    init_db(db_file)
    with patch("website_monitor.db.get_default_db_path", return_value=db_file):
        with patch("website_monitor.config.get_default_db_path", return_value=db_file):
            yield CliRunner(env={"COLUMNS": "200"})


def test_cli_target_lifecycle(runner_with_db: CliRunner):
    res_add = runner_with_db.invoke(
        main,
        ["target", "add", "https://test.example.com", "--name", "CLI Example", "--tag", "prod"],
    )
    assert res_add.exit_code == 0
    assert "Target added successfully" in res_add.output

    res_list = runner_with_db.invoke(main, ["target", "list"])
    assert res_list.exit_code == 0
    assert "CLI Example" in res_list.output
    assert "https://test.example.com" in res_list.output

    res_rm = runner_with_db.invoke(main, ["target", "remove", "1"])
    assert res_rm.exit_code == 0
    assert "Removed target #1" in res_rm.output


def test_cli_check_all(runner_with_db: CliRunner):
    runner_with_db.invoke(main, ["target", "add", "https://check.example.com", "--name", "Check Target"])

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = "Healthy"

    with patch("website_monitor.checker.check_ssl_expiry", return_value=50):
        with patch("httpx.Client.request", return_value=mock_resp):
            res_check = runner_with_db.invoke(main, ["check"])

    assert res_check.exit_code == 0
    assert "Health Check Results" in res_check.output
    assert "Check Target" in res_check.output


def test_cli_stats(runner_with_db: CliRunner):
    runner_with_db.invoke(main, ["target", "add", "https://stats.example.com", "--name", "Stats Target"])
    res_stats = runner_with_db.invoke(main, ["stats"])
    assert res_stats.exit_code == 0
    assert "Global Availability & SLA Overview" in res_stats.output
    assert "Stats Target" in res_stats.output


def test_cli_incidents(runner_with_db: CliRunner):
    res_inc = runner_with_db.invoke(main, ["incidents"])
    assert res_inc.exit_code == 0
    assert "No incidents recorded" in res_inc.output


def test_cli_export(runner_with_db: CliRunner, tmp_path: Path):
    runner_with_db.invoke(main, ["target", "add", "https://export.example.com", "--name", "Export Target"])

    res_export_json = runner_with_db.invoke(main, ["export", "--format", "json"])
    assert res_export_json.exit_code == 0
    assert "summary" in res_export_json.output

    out_file = tmp_path / "out_report.md"
    res_export_file = runner_with_db.invoke(main, ["export", "--format", "md", "--output", str(out_file)])
    assert res_export_file.exit_code == 0
    assert out_file.exists()
    assert "Website Health & SLA Report" in out_file.read_text(encoding="utf-8")


def test_cli_prune(runner_with_db: CliRunner):
    res_prune = runner_with_db.invoke(main, ["prune", "--days", "7"])
    assert res_prune.exit_code == 0
    assert "Pruned" in res_prune.output
