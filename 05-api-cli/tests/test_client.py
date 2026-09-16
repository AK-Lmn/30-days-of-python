from unittest.mock import MagicMock
import httpx
import pytest
from api_cli.client import (
    build_variable_map,
    execute_request,
    interpolate_string,
    resolve_request_config,
)
from api_cli.models import Environment, RequestConfig


def test_interpolate_string(monkeypatch):
    monkeypatch.setenv("GLOBAL_API_KEY", "env_secret_123")
    vars_dict = {"base": "https://api.github.com", "user": "octocat"}

    text = "{{base}}/users/{{user}}?key={{GLOBAL_API_KEY}}"
    interpolated = interpolate_string(text, vars_dict)
    assert interpolated == "https://api.github.com/users/octocat?key=env_secret_123"


def test_resolve_request_config():
    env = Environment(
        name="dev",
        base_url="https://dev.api.io",
        headers={"Authorization": "Bearer {{token}}"},
        variables={"token": "dev_token_1", "version": "v1"},
    )
    config = RequestConfig(
        method="GET",
        url="/{{version}}/users",
        headers={"Custom": "Val"},
        query_params={"limit": "50"},
    )
    resolved = resolve_request_config(config, env)

    assert resolved.url == "https://dev.api.io/v1/users"
    assert resolved.headers["Authorization"] == "Bearer dev_token_1"
    assert resolved.headers["Custom"] == "Val"
    assert resolved.headers["User-Agent"] == "Universal-API-CLI/0.1.0"
    assert resolved.query_params["limit"] == "50"


def test_execute_request_success(tmp_path):
    test_db = tmp_path / "test.db"
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.reason_phrase = "OK"
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.text = '{"message": "success"}'
    mock_resp.content = b'{"message": "success"}'

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = mock_resp

    config = RequestConfig(method="GET", url="https://example.com/api")
    result = execute_request(config, db_path=test_db, client=mock_client)

    assert result.status_code == 200
    assert result.reason_phrase == "OK"
    assert result.parsed_json() == {"message": "success"}
    assert result.is_success is True
    assert result.is_error is False


def test_execute_request_timeout(tmp_path):
    test_db = tmp_path / "test.db"
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.side_effect = httpx.TimeoutException("timed out")

    config = RequestConfig(method="GET", url="https://example.com/api")
    result = execute_request(config, db_path=test_db, client=mock_client)

    assert result.status_code == 504
    assert result.is_error is True
    assert "timed out" in result.body
