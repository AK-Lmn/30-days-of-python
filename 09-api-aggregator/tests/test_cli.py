from pathlib import Path
from click.testing import CliRunner
from api_aggregator.cli import main

runner = CliRunner()


def test_cli_news_command():
    result = runner.invoke(main, ["news", "--mock", "--limit", "2"])
    assert result.exit_code == 0
    assert "Aggregated News" in result.output
    assert "HackerNews" in result.output or "Dev.to" in result.output or "GitHub" in result.output


def test_cli_crypto_command():
    result = runner.invoke(main, ["crypto", "--mock", "--coins", "BTC,ETH"])
    assert result.exit_code == 0
    assert "Reconciled Crypto Rates" in result.output
    assert "BTC" in result.output


def test_cli_weather_command():
    result = runner.invoke(main, ["weather", "--mock", "--city", "Madrid"])
    assert result.exit_code == 0
    assert "Weather" in result.output
    assert "Madrid" in result.output


def test_cli_overview_command():
    result = runner.invoke(main, ["overview", "--mock"])
    assert result.exit_code == 0
    assert "Aggregated Executive Snapshot" in result.output


def test_cli_status_command():
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "Provider Health & Circuit Status" in result.output
    assert "Cache Telemetry" in result.output


def test_cli_benchmark_command():
    result = runner.invoke(main, ["benchmark", "--iterations", "1"])
    assert result.exit_code == 0
    assert "Aggregation Concurrency Benchmark" in result.output
    assert "Parallel" in result.output
    assert "Sequential" in result.output


def test_cli_export_command_json(tmp_path: Path):
    target_file = tmp_path / "news.json"
    result = runner.invoke(
        main,
        ["export", "--domain", "news", "--format", "json", "--output", str(target_file)],
    )
    assert result.exit_code == 0
    assert target_file.exists()
    assert target_file.stat().st_size > 0


def test_cli_export_command_csv(tmp_path: Path):
    target_file = tmp_path / "crypto.csv"
    result = runner.invoke(
        main,
        ["export", "--domain", "crypto", "--format", "csv", "--output", str(target_file)],
    )
    assert result.exit_code == 0
    assert target_file.exists()
    assert target_file.stat().st_size > 0
