import asyncio
import random
from typing import Any, Optional
from urllib.parse import urlparse
import httpx

from api_aggregator.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from api_aggregator.config import CONFIG


class ResilientHttpClient:
    def __init__(
        self,
        timeout_seconds: float = CONFIG.default_timeout_seconds,
        max_retries: int = 2,
        backoff_factor: float = 0.3,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                follow_redirects=True,
                headers={"User-Agent": f"APIAggregator/{CONFIG.app_version}"},
            )
        return self._client

    def get_circuit_breaker(self, provider_name: str) -> CircuitBreaker:
        if provider_name not in self._circuit_breakers:
            self._circuit_breakers[provider_name] = CircuitBreaker(
                name=provider_name,
                failure_threshold=CONFIG.circuit_breaker_failure_threshold,
                recovery_timeout_seconds=CONFIG.circuit_breaker_recovery_timeout_seconds,
                half_open_success_threshold=CONFIG.circuit_breaker_half_open_success_threshold,
            )
        return self._circuit_breakers[provider_name]

    def get_all_circuit_breakers(self) -> dict[str, CircuitBreaker]:
        return dict(self._circuit_breakers)

    async def request(
        self,
        method: str,
        url: str,
        provider_name: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        json_data: Any = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        key = provider_name or urlparse(url).netloc or "default"
        circuit = self.get_circuit_breaker(key)

        if not circuit.allow_request():
            raise CircuitBreakerOpenException(
                f"Circuit breaker is OPEN for {key}"
            )

        client = await self._get_client()
        request_timeout = timeout or self.timeout_seconds
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    json=json_data,
                    timeout=request_timeout,
                )
                if response.status_code >= 500:
                    circuit.record_failure()
                    if attempt < self.max_retries:
                        delay = (self.backoff_factor * (2**attempt)) + random.uniform(0.05, 0.15)
                        await asyncio.sleep(delay)
                        continue
                else:
                    circuit.record_success()
                    return response
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                circuit.record_failure()
                last_exception = exc
                if attempt < self.max_retries:
                    delay = (self.backoff_factor * (2**attempt)) + random.uniform(0.05, 0.15)
                    await asyncio.sleep(delay)
                    continue

        if last_exception is not None:
            raise last_exception

        return response

    async def get(
        self,
        url: str,
        provider_name: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        return await self.request(
            method="GET",
            url=url,
            provider_name=provider_name,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    async def post(
        self,
        url: str,
        provider_name: Optional[str] = None,
        json_data: Any = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        return await self.request(
            method="POST",
            url=url,
            provider_name=provider_name,
            headers=headers,
            json_data=json_data,
            timeout=timeout,
        )

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "ResilientHttpClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
