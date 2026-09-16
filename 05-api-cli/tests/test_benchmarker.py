from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from api_cli.benchmarker import async_run_benchmark, calculate_stats
from api_cli.models import RequestConfig


def test_calculate_stats_empty():
    stats = calculate_stats([], {}, 0.0)
    assert stats.total_requests == 0
    assert stats.min_latency_ms == 0.0


def test_calculate_stats_normal():
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
    status_codes = {200: 4, 500: 1}
    stats = calculate_stats(latencies, status_codes, 2.0)

    assert stats.total_requests == 5
    assert stats.successful_requests == 4
    assert stats.failed_requests == 1
    assert stats.min_latency_ms == 10.0
    assert stats.max_latency_ms == 50.0
    assert stats.avg_latency_ms == 30.0
    assert stats.median_latency_ms == 30.0
    assert stats.requests_per_second == 2.5


@pytest.mark.asyncio
async def test_async_run_benchmark():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)

    config = RequestConfig(method="GET", url="https://test.local")

    with patch("api_cli.benchmarker.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = mock_client
        stats = await async_run_benchmark(config, total_requests=4, concurrency=2)

    assert stats.total_requests == 4
    assert stats.successful_requests == 4
    assert stats.status_code_counts[200] == 4
