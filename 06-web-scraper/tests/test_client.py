from unittest.mock import MagicMock
import httpx
from web_scraper.client import HttpClient


def test_fetch_success():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.url = httpx.URL("https://example.com")
    mock_resp.status_code = 200
    mock_resp.text = "<html><body>Hello</body></html>"
    mock_resp.is_success = True

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    client = HttpClient(client=mock_client)
    res = client.fetch("https://example.com")

    assert res.is_success is True
    assert res.status_code == 200
    assert "Hello" in res.html
    assert res.latency_ms >= 0.0


def test_fetch_with_headers_and_cookies():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.url = httpx.URL("https://example.com")
    mock_resp.status_code = 200
    mock_resp.text = "OK"
    mock_resp.is_success = True

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    client = HttpClient(client=mock_client, default_headers={"X-Default": "1"})
    client.fetch("https://example.com", headers={"X-Custom": "2"}, cookies={"session": "abc"})

    mock_client.get.assert_called_once()
    call_kwargs = mock_client.get.call_args[1]
    assert call_kwargs["headers"]["X-Default"] == "1"
    assert call_kwargs["headers"]["X-Custom"] == "2"
    mock_client.cookies.update.assert_called_once_with({"session": "abc"})


def test_fetch_retry_on_503():
    fail_resp = MagicMock(spec=httpx.Response)
    fail_resp.status_code = 503
    fail_resp.headers = {}
    fail_resp.is_success = False

    success_resp = MagicMock(spec=httpx.Response)
    success_resp.url = httpx.URL("https://example.com")
    success_resp.status_code = 200
    success_resp.headers = {}
    success_resp.text = "Recovered"
    success_resp.is_success = True

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [fail_resp, success_resp]

    client = HttpClient(client=mock_client)
    res = client.fetch("https://example.com", max_retries=2, backoff_factor=0.01)

    assert mock_client.get.call_count == 2
    assert res.is_success is True
    assert res.status_code == 200
    assert res.html == "Recovered"


def test_fetch_exhausted_retries():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.ConnectTimeout("Connection timed out")

    client = HttpClient(client=mock_client)
    res = client.fetch("https://example.com/unreachable", max_retries=2, backoff_factor=0.01)

    assert mock_client.get.call_count == 3
    assert res.is_success is False
    assert res.status_code == 0
    assert "ConnectTimeout" in (res.error or "")
