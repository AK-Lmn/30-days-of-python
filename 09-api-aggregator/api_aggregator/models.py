from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class AggregateStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    ERROR = "ERROR"


class UnifiedNewsItem(BaseModel):
    id: str
    title: str
    url: str
    author: str = "Unknown"
    score: int = 0
    comments_count: int = 0
    source: str
    published_at: str
    tags: list[str] = Field(default_factory=list)


class UnifiedCryptoRate(BaseModel):
    symbol: str
    name: str
    price_usd: float
    change_24h_percent: float = 0.0
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None
    sources: list[str] = Field(default_factory=list)
    discrepancy_percent: float = 0.0


class UnifiedWeatherReport(BaseModel):
    location: str
    latitude: float
    longitude: float
    temperature_c: float
    temperature_f: float
    humidity_percent: float
    wind_speed_kmh: float
    condition: str
    sources: list[str] = Field(default_factory=list)
    timestamp: str


class CustomEndpointRequest(BaseModel):
    urls: list[str]
    timeout_seconds: float = 5.0
    headers: dict[str, str] = Field(default_factory=dict)


class CustomEndpointResult(BaseModel):
    url: str
    status_code: Optional[int] = None
    latency_ms: float = 0.0
    data: Any = None
    error: Optional[str] = None


class ProviderHealth(BaseModel):
    provider_name: str
    domain: str
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_latency_ms: float = 0.0
    is_healthy: bool = True
    error_count: int = 0
    success_count: int = 0


class AggregationMetrics(BaseModel):
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_latency_ms: float = 0.0
    provider_stats: dict[str, ProviderHealth] = Field(default_factory=dict)


class UnifiedEnvelope(BaseModel, Generic[T]):
    status: AggregateStatus
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    latency_ms: float
    sources_queried: list[str] = Field(default_factory=list)
    sources_succeeded: list[str] = Field(default_factory=list)
    sources_failed: list[str] = Field(default_factory=list)
    cached: bool = False
    count: int = 0
    data: T
    error: Optional[str] = None


class UnifiedOverview(BaseModel):
    timestamp: str
    news_count: int
    top_news: list[UnifiedNewsItem] = Field(default_factory=list)
    crypto_rates: list[UnifiedCryptoRate] = Field(default_factory=list)
    weather: Optional[UnifiedWeatherReport] = None
    latency_ms: float = 0.0
