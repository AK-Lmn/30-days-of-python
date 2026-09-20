from abc import ABC, abstractmethod
from typing import Any
from api_aggregator.client import ResilientHttpClient
from api_aggregator.models import ProviderHealth


class BaseProvider(ABC):
    def __init__(self, name: str, domain: str, enabled: bool = True) -> None:
        self.name = name
        self.domain = domain
        self.enabled = enabled
        self.success_count = 0
        self.error_count = 0
        self.consecutive_failures = 0
        self.last_latency_ms = 0.0

    @abstractmethod
    async def fetch(self, client: ResilientHttpClient, **kwargs: Any) -> Any:
        pass

    @abstractmethod
    def fallback(self, **kwargs: Any) -> Any:
        pass

    def record_success(self, latency_ms: float) -> None:
        self.success_count += 1
        self.consecutive_failures = 0
        self.last_latency_ms = latency_ms

    def record_failure(self, latency_ms: float) -> None:
        self.error_count += 1
        self.consecutive_failures += 1
        self.last_latency_ms = latency_ms

    def get_health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name=self.name,
            domain=self.domain,
            consecutive_failures=self.consecutive_failures,
            last_latency_ms=self.last_latency_ms,
            is_healthy=self.consecutive_failures == 0,
            error_count=self.error_count,
            success_count=self.success_count,
        )
