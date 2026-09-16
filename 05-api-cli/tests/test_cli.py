from unittest.mock import MagicMock, patch
from click.testing import CliRunner
import pytest
from api_cli.cli import main
from api_cli.models import BenchmarkStats, ResponseResult


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_help(runner):
    res = runner.invoke(main, ["--help"])
    assert res.exit_code == 0
    assert "api-cli" in res.output or "Universal API CLI" in res.output or "Usage:" in res.output


def test_cli_get(runner):
    mock_result = ResponseResult(
        status_code=200,
        reason_phrase="OK",
        headers={"content-type": "application/json"},
        body='{"status": "ok"}',
        latency_ms=12.5,
        content_type="application/json",
        size_bytes=16,
    )
    with patch("api_cli.cli.execute_request", return_value=mock_result):
        res = runner.invoke(main, ["get", "https://api.example.com/test"])
        assert res.exit_code == 0
        assert "200 OK" in res.output
        assert "status" in res.output


def test_cli_post(runner):
    mock_result = ResponseResult(
        status_code=201,
        reason_phrase="Created",
        headers={"content-type": "application/json"},
        body='{"id": 42}',
        latency_ms=25.0,
        content_type="application/json",
        size_bytes=10,
    )
    with patch("api_cli.cli.execute_request", return_value=mock_result):
        res = runner.invoke(main, ["post", "https://api.example.com/items", "-d", '{"name":"widget"}'])
        assert res.exit_code == 0
        assert "201 Created" in res.output
        assert "42" in res.output


def test_cli_env_flow(runner, tmp_path, monkeypatch):
    test_db = tmp_path / "cli_test.db"
    monkeypatch.setenv("API_CLI_DB", str(test_db))

    res = runner.invoke(main, ["env", "set", "staging", "--base-url", "https://staging.api.com", "-v", "api_key=secret_xyz"])
    assert res.exit_code == 0
    assert "Saved environment: staging" in res.output

    res = runner.invoke(main, ["env", "list"])
    assert res.exit_code == 0
    assert "staging" in res.output

    res = runner.invoke(main, ["env", "use", "staging"])
    assert res.exit_code == 0
    assert "Active environment switched to: staging" in res.output

    res = runner.invoke(main, ["env", "current"])
    assert res.exit_code == 0
    assert "staging" in res.output
    assert "https://staging.api.com" in res.output

    res = runner.invoke(main, ["env", "show", "staging"])
    assert res.exit_code == 0
    assert "https://staging.api.com" in res.output
    assert "api_key" in res.output

    res = runner.invoke(main, ["env", "delete", "staging"])
    assert res.exit_code == 0
    assert "Deleted environment: staging" in res.output


def test_cli_saved_requests_flow(runner, tmp_path, monkeypatch):
    test_db = tmp_path / "cli_test.db"
    monkeypatch.setenv("API_CLI_DB", str(test_db))

    res = runner.invoke(main, ["saved", "save", "list_todos", "https://jsonplaceholder.typicode.com/todos", "-X", "GET"])
    assert res.exit_code == 0
    assert "Saved request: list_todos" in res.output

    res = runner.invoke(main, ["saved", "list"])
    assert res.exit_code == 0
    assert "list_todos" in res.output

    mock_result = ResponseResult(
        status_code=200,
        reason_phrase="OK",
        headers={"content-type": "application/json"},
        body='[{"id": 1, "title": "delectus"}]',
        latency_ms=15.0,
        content_type="application/json",
        size_bytes=30,
    )
    with patch("api_cli.cli.execute_request", return_value=mock_result):
        res = runner.invoke(main, ["saved", "run", "list_todos"])
        assert res.exit_code == 0
        assert "200 OK" in res.output
        assert "delectus" in res.output

    res = runner.invoke(main, ["saved", "delete", "list_todos"])
    assert res.exit_code == 0
    assert "Deleted saved request: list_todos" in res.output


def test_cli_history_flow(runner, tmp_path, monkeypatch):
    test_db = tmp_path / "cli_test.db"
    monkeypatch.setenv("API_CLI_DB", str(test_db))

    mock_result = ResponseResult(
        status_code=200,
        reason_phrase="OK",
        headers={"content-type": "application/json"},
        body='{"echo": true}',
        latency_ms=10.0,
        content_type="application/json",
        size_bytes=14,
    )
    with patch("api_cli.cli.execute_request", return_value=mock_result):
        runner.invoke(main, ["get", "https://api.example.com/echo"])

    with patch("api_cli.cli.get_history_entry") as mock_get_hist:
        mock_get_hist.return_value = MagicMock(
            id=1,
            timestamp="2026-09-16T12:00:00Z",
            method="GET",
            url="https://api.example.com/echo",
            status_code=200,
            latency_ms=10.0,
            request_headers={},
            request_body=None,
            response_headers={},
            response_body='{"echo": true}',
        )
        res = runner.invoke(main, ["history", "show", "1"])
        assert res.exit_code == 0
        assert "200" in res.output

    res = runner.invoke(main, ["history", "clear"])
    assert res.exit_code == 0
    assert "Cleared" in res.output


def test_cli_bench(runner):
    mock_stats = BenchmarkStats(
        total_requests=5,
        successful_requests=5,
        failed_requests=0,
        total_time_seconds=0.5,
        requests_per_second=10.0,
        min_latency_ms=8.0,
        avg_latency_ms=12.0,
        median_latency_ms=11.0,
        p95_latency_ms=15.0,
        p99_latency_ms=15.0,
        max_latency_ms=16.0,
        status_code_counts={200: 5},
    )
    with patch("api_cli.cli.run_benchmark", return_value=mock_stats):
        res = runner.invoke(main, ["bench", "https://api.example.com", "-n", "5", "-c", "2"])
        assert res.exit_code == 0
        assert "Benchmark Summary" in res.output
        assert "10.00 req/s" in res.output
