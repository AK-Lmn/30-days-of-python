import asyncio
import time
from typing import Any
from api_aggregator.client import ResilientHttpClient
from api_aggregator.models import CustomEndpointResult
from api_aggregator.providers.base import BaseProvider


class CustomEndpointsProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="custom", domain="custom")

    async def fetch(
        self,
        client: ResilientHttpClient,
        urls: list[str] | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 5.0,
        **kwargs: Any,
    ) -> list[CustomEndpointResult]:
        target_urls = urls or []
        if not target_urls:
            return []

        async def fetch_single(url: str) -> CustomEndpointResult:
            start = time.perf_counter()
            try:
                res = await client.get(
                    url,
                    provider_name=f"custom-{url}",
                    headers=headers,
                    timeout=timeout_seconds,
                )
                latency = round((time.perf_counter() - start) * 1000.0, 2)
                try:
                    data = res.json()
                except Exception:
                    data = res.text
                return CustomEndpointResult(
                    url=url,
                    status_code=res.status_code,
                    latency_ms=latency,
                    data=data,
                )
            except Exception as exc:
                latency = round((time.perf_counter() - start) * 1000.0, 2)
                return CustomEndpointResult(
                    url=url,
                    status_code=None,
                    latency_ms=latency,
                    error=str(exc),
                )

        results = await asyncio.gather(
            *(fetch_single(url) for url in target_urls),
            return_exceptions=False,
        )
        return list(results)

    def fallback(
        self, urls: list[str] | None = None, **kwargs: Any
    ) -> list[CustomEndpointResult]:
        target_urls = urls or ["https://httpbin.org/get"]
        return [
            CustomEndpointResult(
                url=u,
                status_code=200,
                latency_ms=12.5,
                data={"origin": "127.0.0.1", "mock": True},
            )
            for u in target_urls
        ]
