import os
from datetime import datetime, timezone
from typing import Any, Optional
import httpx

from github_analyzer.cache import ResponseCache
from github_analyzer.models import RateLimitStatus


class GitHubAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ResourceNotFoundError(GitHubAPIError):
    pass


class RateLimitExceededError(GitHubAPIError):
    pass


class AuthenticationError(GitHubAPIError):
    pass


class GitHubClient:
    def __init__(
        self,
        token: Optional[str] = None,
        cache: Optional[ResponseCache] = None,
        base_url: str = "https://api.github.com",
        use_cache: bool = True,
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.use_cache = use_cache
        self.cache = cache if cache is not None else (ResponseCache() if use_cache else None)
        self.timeout = timeout

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GitHub-Analyzer-CLI",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self._headers = headers

    def _build_url(self, endpoint: str) -> str:
        clean_endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{clean_endpoint}"

    def _build_cache_key(self, endpoint: str, params: Optional[dict[str, Any]]) -> str:
        param_str = ""
        if params:
            sorted_items = sorted((str(k), str(v)) for k, v in params.items())
            param_str = "?" + "&".join(f"{k}={v}" for k, v in sorted_items)
        return f"{endpoint}{param_str}"

    def request(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        bypass_cache: bool = False,
        ttl_seconds: int = 3600,
    ) -> Any:
        cache_key = self._build_cache_key(endpoint, params)
        if self.use_cache and self.cache and not bypass_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        url = self._build_url(endpoint)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=self._headers, params=params)
        except httpx.RequestError as exc:
            raise GitHubAPIError(f"Network error communicating with GitHub: {exc}")

        if response.status_code == 404:
            raise ResourceNotFoundError(f"Resource not found: {endpoint}", status_code=404)
        if response.status_code == 401:
            raise AuthenticationError("Invalid or expired GitHub token.", status_code=401)
        if response.status_code == 403:
            remaining = response.headers.get("x-ratelimit-remaining", "0")
            if remaining == "0":
                reset_timestamp = int(response.headers.get("x-ratelimit-reset", 0))
                reset_dt = datetime.fromtimestamp(reset_timestamp, tz=timezone.utc)
                raise RateLimitExceededError(
                    f"GitHub API rate limit exceeded. Resets at {reset_dt.isoformat()}.",
                    status_code=403,
                )
            raise GitHubAPIError(f"GitHub API forbidden: {response.text}", status_code=403)
        if response.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API request failed ({response.status_code}): {response.text}",
                status_code=response.status_code,
            )

        data = response.json()
        if self.use_cache and self.cache:
            self.cache.set(cache_key, data, ttl_seconds=ttl_seconds)

        return data

    def get_user(self, username: str) -> dict[str, Any]:
        return self.request(f"users/{username}")

    def get_user_repos(
        self,
        username: str,
        sort: str = "updated",
        per_page: int = 100,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        params = {"sort": sort, "per_page": per_page, "page": page}
        return self.request(f"users/{username}/repos", params=params)

    def get_all_user_repos(
        self,
        username: str,
        max_repos: int = 300,
    ) -> list[dict[str, Any]]:
        all_repos: list[dict[str, Any]] = []
        page = 1
        while len(all_repos) < max_repos:
            batch = self.get_user_repos(username, page=page, per_page=100)
            if not batch:
                break
            all_repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return all_repos[:max_repos]

    def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        return self.request(f"repos/{owner}/{repo}")

    def get_repo_languages(self, owner: str, repo: str) -> dict[str, int]:
        return self.request(f"repos/{owner}/{repo}/languages")

    def get_repo_commits(
        self,
        owner: str,
        repo: str,
        per_page: int = 50,
    ) -> list[dict[str, Any]]:
        params = {"per_page": per_page}
        return self.request(f"repos/{owner}/{repo}/commits", params=params)

    def get_repo_contributors(
        self,
        owner: str,
        repo: str,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        params = {"per_page": per_page}
        try:
            return self.request(f"repos/{owner}/{repo}/contributors", params=params)
        except GitHubAPIError:
            return []

    def get_rate_limit(self) -> RateLimitStatus:
        data = self.request("rate_limit", bypass_cache=True)
        core = data.get("resources", {}).get("core", {})
        limit = core.get("limit", 60)
        remaining = core.get("remaining", 0)
        used = core.get("used", limit - remaining)
        reset_ts = core.get("reset", int(datetime.now(timezone.utc).timestamp()))
        reset_dt = datetime.fromtimestamp(reset_ts, tz=timezone.utc)
        return RateLimitStatus(
            limit=limit,
            remaining=remaining,
            reset_time=reset_dt,
            used=used,
        )
