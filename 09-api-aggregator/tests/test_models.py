from api_aggregator.models import (
    AggregateStatus,
    AggregationMetrics,
    CircuitState,
    CustomEndpointResult,
    ProviderHealth,
    UnifiedCryptoRate,
    UnifiedEnvelope,
    UnifiedNewsItem,
    UnifiedOverview,
    UnifiedWeatherReport,
)


def test_unified_news_item_creation():
    item = UnifiedNewsItem(
        id="test-1",
        title="Python 3.13 Released",
        url="https://python.org",
        author="core-team",
        score=100,
        comments_count=20,
        source="Official",
        published_at="2026-09-20T00:00:00Z",
        tags=["python", "release"],
    )
    assert item.id == "test-1"
    assert item.score == 100
    assert "release" in item.tags


def test_unified_crypto_rate_creation():
    rate = UnifiedCryptoRate(
        symbol="BTC",
        name="Bitcoin",
        price_usd=68000.50,
        change_24h_percent=2.1,
        high_24h=69000.0,
        low_24h=67000.0,
        sources=["CoinGecko", "Coinbase"],
        discrepancy_percent=0.15,
    )
    assert rate.symbol == "BTC"
    assert rate.price_usd == 68000.50
    assert len(rate.sources) == 2
    assert rate.discrepancy_percent == 0.15


def test_unified_weather_report_creation():
    rep = UnifiedWeatherReport(
        location="Tokyo, Japan",
        latitude=35.6762,
        longitude=139.6503,
        temperature_c=22.0,
        temperature_f=71.6,
        humidity_percent=55.0,
        wind_speed_kmh=10.5,
        condition="Clear sky",
        sources=["Open-Meteo"],
        timestamp="2026-09-20T12:00:00Z",
    )
    assert rep.location == "Tokyo, Japan"
    assert rep.temperature_c == 22.0
    assert rep.temperature_f == 71.6


def test_unified_envelope_serialization():
    item = UnifiedNewsItem(
        id="item-1",
        title="Headline",
        url="https://example.com",
        source="News",
        published_at="2026-09-20T00:00:00Z",
    )
    envelope = UnifiedEnvelope[list[UnifiedNewsItem]](
        status=AggregateStatus.SUCCESS,
        latency_ms=45.2,
        sources_queried=["hn", "gh"],
        sources_succeeded=["hn", "gh"],
        sources_failed=[],
        cached=False,
        count=1,
        data=[item],
    )
    dumped = envelope.model_dump()
    assert dumped["status"] == "SUCCESS"
    assert dumped["count"] == 1
    assert dumped["latency_ms"] == 45.2
    assert len(dumped["data"]) == 1
    assert dumped["data"][0]["title"] == "Headline"


def test_provider_health_model():
    health = ProviderHealth(
        provider_name="test_api",
        domain="news",
        circuit_state=CircuitState.CLOSED,
        consecutive_failures=0,
        last_latency_ms=12.4,
        is_healthy=True,
    )
    assert health.is_healthy is True
    assert health.circuit_state == CircuitState.CLOSED


def test_custom_endpoint_result_model():
    result = CustomEndpointResult(
        url="https://api.test/data",
        status_code=200,
        latency_ms=35.0,
        data={"key": "val"},
    )
    assert result.status_code == 200
    assert result.error is None
    assert result.data["key"] == "val"


def test_overview_model():
    overview = UnifiedOverview(
        timestamp="2026-09-20T12:00:00Z",
        news_count=0,
        top_news=[],
        crypto_rates=[],
        weather=None,
        latency_ms=15.0,
    )
    assert overview.news_count == 0
    assert overview.weather is None
