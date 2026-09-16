from unittest.mock import patch, MagicMock, AsyncMock
import httpx
import pytest
from website_monitor.checker import check_target, async_check_target, parse_hostname
from website_monitor.models import MonitorTarget


def test_parse_hostname():
    assert parse_hostname("https://example.com/test") == "example.com"
    assert parse_hostname("http://sub.domain.org:8080/path") == "sub.domain.org"
    assert parse_hostname("invalid-url") is None


def test_check_target_success_200():
    target = MonitorTarget(url="https://example.com", name="Example")
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = "Hello World"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = mock_resp

    with patch("website_monitor.checker.check_ssl_expiry", return_value=45):
        result = check_target(target, client=mock_client)

    assert result.is_up is True
    assert result.status_code == 200
    assert result.ssl_days_left == 45
    assert result.error_message is None


def test_check_target_status_mismatch():
    target = MonitorTarget(url="https://example.com", name="Example", expected_status=200)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 502
    mock_resp.text = "Bad Gateway"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = mock_resp

    with patch("website_monitor.checker.check_ssl_expiry", return_value=30):
        result = check_target(target, client=mock_client)

    assert result.is_up is False
    assert result.status_code == 502
    assert "Expected status 200, received 502" in result.error_message


def test_check_target_keyword_matched():
    target = MonitorTarget(
        url="https://example.com",
        name="Example",
        keyword="Operational",
    )
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = "Status: Operational and healthy"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = mock_resp

    with patch("website_monitor.checker.check_ssl_expiry", return_value=30):
        result = check_target(target, client=mock_client)

    assert result.is_up is True
    assert result.error_message is None


def test_check_target_keyword_missing():
    target = MonitorTarget(
        url="https://example.com",
        name="Example",
        keyword="Operational",
    )
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = "Status: Maintenance mode"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = mock_resp

    with patch("website_monitor.checker.check_ssl_expiry", return_value=30):
        result = check_target(target, client=mock_client)

    assert result.is_up is False
    assert "Keyword \"Operational\" missing" in result.error_message


def test_check_target_timeout():
    target = MonitorTarget(url="https://example.com", name="Example", timeout_seconds=2.0)
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.side_effect = httpx.TimeoutException("timed out")

    with patch("website_monitor.checker.check_ssl_expiry", return_value=None):
        result = check_target(target, client=mock_client)

    assert result.is_up is False
    assert result.status_code is None
    assert "timed out" in result.error_message


def test_check_target_connect_error():
    target = MonitorTarget(url="https://example.com", name="Example")
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.side_effect = httpx.ConnectError("refused")

    with patch("website_monitor.checker.check_ssl_expiry", return_value=None):
        result = check_target(target, client=mock_client)

    assert result.is_up is False
    assert result.status_code is None
    assert "Connection failed" in result.error_message


@pytest.mark.asyncio
async def test_async_check_target():
    target = MonitorTarget(url="https://example.com", name="Example")
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = "OK"

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=mock_resp)

    with patch("website_monitor.checker.check_ssl_expiry", return_value=60):
        result = await async_check_target(target, client=mock_client)

    assert result.is_up is True
    assert result.status_code == 200
    assert result.ssl_days_left == 60
