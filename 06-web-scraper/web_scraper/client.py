import time
import httpx
from web_scraper.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
)
from web_scraper.models import PageResponse

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class HttpClient:
    def __init__(
        self,
        client: httpx.Client | None = None,
        default_headers: dict[str, str] | None = None,
        default_cookies: dict[str, str] | None = None,
    ) -> None:
        self._external_client = client
        self.default_headers = default_headers or {}
        self.default_cookies = default_cookies or {}

    def fetch(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        user_agent: str | None = None,
    ) -> PageResponse:
        merged_headers = {"User-Agent": user_agent or DEFAULT_USER_AGENT}
        merged_headers.update(self.default_headers)
        if headers:
            merged_headers.update(headers)

        merged_cookies = dict(self.default_cookies)
        if cookies:
            merged_cookies.update(cookies)

        last_error: str | None = None
        attempt = 0

        while attempt <= max_retries:
            attempt += 1
            start_time = time.perf_counter()

            try:
                if self._external_client is not None:
                    if merged_cookies and hasattr(self._external_client, "cookies"):
                        self._external_client.cookies.update(merged_cookies)
                    response = self._external_client.get(
                        url,
                        headers=merged_headers,
                        timeout=timeout,
                        follow_redirects=True,
                    )
                else:
                    with httpx.Client(
                        timeout=timeout,
                        follow_redirects=True,
                        cookies=merged_cookies,
                    ) as direct_client:
                        response = direct_client.get(
                            url,
                            headers=merged_headers,
                        )

                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if response.status_code in RETRYABLE_STATUS_CODES and attempt <= max_retries:
                    resp_headers = getattr(response, "headers", {}) or {}
                    retry_after = resp_headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        sleep_time = float(retry_after)
                    else:
                        sleep_time = backoff_factor * (2 ** (attempt - 1))
                    time.sleep(sleep_time)
                    continue

                return PageResponse(
                    url=str(response.url),
                    status_code=response.status_code,
                    html=response.text,
                    latency_ms=round(latency_ms, 2),
                    error=None if response.is_success else f"HTTP {response.status_code}",
                )

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt <= max_retries:
                    sleep_time = backoff_factor * (2 ** (attempt - 1))
                    time.sleep(sleep_time)
                else:
                    break

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return PageResponse(
            url=url,
            status_code=0,
            html="",
            latency_ms=round(latency_ms, 2),
            error=last_error or "Maximum retries exceeded",
        )
