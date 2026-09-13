from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from github_analyzer.cache import ResponseCache
from github_analyzer.client import (
    AuthenticationError,
    GitHubAPIError,
    GitHubClient,
    RateLimitExceededError,
    ResourceNotFoundError,
)


def test_client_init_headers():
    client_no_token = GitHubClient(token=None, use_cache=False)
    assert "Authorization" not in client_no_token._headers
    assert client_no_token._headers["User-Agent"] == "GitHub-Analyzer-CLI"

    client_with_token = GitHubClient(token="test-secret-token", use_cache=False)
    assert client_with_token._headers["Authorization"] == "Bearer test-secret-token"


def test_client_cache_hit(tmp_path: Path):
    cache = ResponseCache(db_path=tmp_path / "cache.db")
    cache.set("users/torvalds", {"login": "torvalds", "id": 1024025})

    client = GitHubClient(cache=cache, use_cache=True)
    with patch("httpx.Client") as mock_client:
        data = client.get_user("torvalds")
        assert data["login"] == "torvalds"
        mock_client.assert_not_called()


def test_client_resource_not_found():
    client = GitHubClient(use_cache=False)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = '{"message": "Not Found"}'

    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.get.return_value = mock_response
        mock_client_cls.return_value = mock_instance

        with pytest.raises(ResourceNotFoundError):
            client.get_user("nonexistent_user_9999999")


def test_client_authentication_error():
    client = GitHubClient(token="invalid_token", use_cache=False)
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = '{"message": "Bad credentials"}'

    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.get.return_value = mock_response
        mock_client_cls.return_value = mock_instance

        with pytest.raises(AuthenticationError):
            client.get_user("octocat")


def test_client_rate_limit_exceeded():
    client = GitHubClient(use_cache=False)
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1700000000"}
    mock_response.text = '{"message": "API rate limit exceeded"}'

    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.get.return_value = mock_response
        mock_client_cls.return_value = mock_instance

        with pytest.raises(RateLimitExceededError):
            client.get_user("octocat")


def test_client_get_rate_limit():
    client = GitHubClient(use_cache=False)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "resources": {
            "core": {
                "limit": 5000,
                "remaining": 4980,
                "reset": 1700000000,
                "used": 20,
            }
        }
    }

    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.get.return_value = mock_response
        mock_client_cls.return_value = mock_instance

        status = client.get_rate_limit()
        assert status.limit == 5000
        assert status.remaining == 4980
        assert status.used == 20
