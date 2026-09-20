import pytest
from api_aggregator.engine import AggregationEngine
from api_aggregator.models import AggregateStatus


@pytest.mark.asyncio
async def test_engine_aggregate_news_mock():
    engine = AggregationEngine()
    try:
        envelope = await engine.aggregate_news(limit=3, force_mock=True)
        assert envelope.status in (AggregateStatus.SUCCESS, AggregateStatus.PARTIAL)
        assert len(envelope.data) <= 3
        assert envelope.cached is False
        assert "hackernews" in envelope.sources_queried

        cached_envelope = await engine.aggregate_news(limit=3, force_mock=True)
        assert cached_envelope.cached is True
        assert len(cached_envelope.data) == len(envelope.data)
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_engine_aggregate_crypto_reconciliation():
    engine = AggregationEngine()
    try:
        envelope = await engine.aggregate_crypto(
            symbols=["BTC", "ETH"], force_mock=True
        )
        assert envelope.status in (AggregateStatus.SUCCESS, AggregateStatus.PARTIAL)
        assert len(envelope.data) == 2

        btc_rate = next((r for r in envelope.data if r.symbol == "BTC"), None)
        assert btc_rate is not None
        assert btc_rate.price_usd > 0
        assert len(btc_rate.sources) >= 2
        assert btc_rate.discrepancy_percent >= 0.0
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_engine_aggregate_weather():
    engine = AggregationEngine()
    try:
        envelope = await engine.aggregate_weather(city="London", force_mock=True)
        assert envelope.status in (AggregateStatus.SUCCESS, AggregateStatus.PARTIAL)
        assert envelope.data is not None
        assert envelope.data.location == "London"
        assert envelope.data.temperature_c > 0
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_engine_aggregate_overview():
    engine = AggregationEngine()
    try:
        envelope = await engine.aggregate_overview(force_mock=True)
        assert envelope.status in (AggregateStatus.SUCCESS, AggregateStatus.PARTIAL)
        assert envelope.data.weather is not None
        assert len(envelope.data.crypto_rates) > 0
        assert len(envelope.data.top_news) > 0
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_engine_aggregate_custom():
    engine = AggregationEngine()
    try:
        envelope = await engine.aggregate_custom(
            urls=["https://example.com/api1", "https://example.com/api2"],
            force_mock=True,
        )
        assert len(envelope.data) == 2
        assert envelope.count == 2
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_engine_metrics_telemetry():
    engine = AggregationEngine()
    try:
        await engine.aggregate_news(limit=2, force_mock=True)
        metrics = await engine.get_metrics()
        assert metrics.total_requests >= 1
        assert "hackernews" in metrics.provider_stats
    finally:
        await engine.close()
