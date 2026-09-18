from unittest.mock import patch
from click.testing import CliRunner
from web_scraper.cli import main
from web_scraper.models import PageResponse


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Web Scraper" in result.output or "Usage" in result.output


def test_cli_preset_list():
    runner = CliRunner()
    result = runner.invoke(main, ["preset", "list"])
    assert result.exit_code == 0
    assert "quotes" in result.output
    assert "books" in result.output


def test_cli_cache_commands():
    runner = CliRunner()
    stats_res = runner.invoke(main, ["cache", "stats"])
    assert stats_res.exit_code == 0
    assert "Cached responses" in stats_res.output

    clear_res = runner.invoke(main, ["cache", "clear"])
    assert clear_res.exit_code == 0
    assert "Cleared" in clear_res.output


@patch("web_scraper.client.HttpClient.fetch")
def test_cli_test_selector(mock_fetch):
    mock_fetch.return_value = PageResponse(
        url="https://example.com",
        status_code=200,
        html="<html><body><h1>Test Header</h1></body></html>",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["test-selector", "https://example.com", "h1"])
    assert result.exit_code == 0
    assert "Test Header" in result.output


@patch("web_scraper.robots.RobotsChecker.can_fetch")
@patch("web_scraper.robots.RobotsChecker.get_crawl_delay")
def test_cli_robots_command(mock_delay, mock_can_fetch):
    mock_can_fetch.return_value = True
    mock_delay.return_value = 1.0

    runner = CliRunner()
    result = runner.invoke(main, ["robots", "https://example.com/page"])
    assert result.exit_code == 0
    assert "ALLOWED" in result.output
    assert "1.0s" in result.output


@patch("web_scraper.client.HttpClient.fetch")
def test_cli_run_command(mock_fetch, tmp_path):
    mock_fetch.return_value = PageResponse(
        url="https://example.com",
        status_code=200,
        html='<div class="item"><h2>Widget</h2></div>',
    )
    export_file = tmp_path / "result.json"

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "run",
            "https://example.com",
            "--container",
            "div.item",
            "-f",
            "title:h2:text",
            "-o",
            str(export_file),
            "--no-robots",
        ],
    )
    assert result.exit_code == 0
    assert export_file.exists()
