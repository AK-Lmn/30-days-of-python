import pytest
from api_aggregator.client import ResilientHttpClient
from api_aggregator.providers.crypto import (
    BinanceProvider,
    CoinbaseProvider,
    CoinGeckoProvider,
)
from api_aggregator.providers.custom import CustomEndpointsProvider
from api_aggregator.providers.news import (
    DevToProvider,
    GitHubEventsProvider,
    HackerNewsProvider,
)
from api_aggregator.providers.weather import OpenMeteoProvider, WttrInProvider


def test_hackernews_provider_fallback():
    provider = HackerNewsProvider()
    items = provider.fallback(limit=2)
    assert len(items) == 2
    assert items[0].source == "HackerNews"
    assert items[0].title != ""


def test_github_provider_fallback():
    provider = GitHubEventsProvider()
    items = provider.fallback(limit=1)
    assert len(items) == 1
    assert items[0].source == "GitHub"


def test_devto_provider_fallback():
    provider = DevToProvider()
    items = provider.fallback(limit=2)
    assert len(items) == 2
    assert items[0].source == "Dev.to"


def test_coingecko_provider_fallback():
    provider = CoinGeckoProvider()
    rates = provider.fallback(symbols=["BTC", "ETH"])
    assert len(rates) == 2
    syms = [r.symbol for r in rates]
    assert "BTC" in syms
    assert "ETH" in syms


def test_coinbase_provider_fallback():
    provider = CoinbaseProvider()
    rates = provider.fallback(symbols=["BTC"])
    assert len(rates) == 1
    assert rates[0].symbol == "BTC"
    assert rates[0].sources == ["Coinbase"]


def test_binance_provider_fallback():
    provider = BinanceProvider()
    rates = provider.fallback(symbols=["SOL"])
    assert len(rates) == 1
    assert rates[0].symbol == "SOL"
    assert rates[0].high_24h is not None


def test_openmeteo_provider_fallback():
    provider = OpenMeteoProvider()
    report = provider.fallback(city="Berlin")
    assert report.location == "Berlin"
    assert report.temperature_c == 18.5
    assert report.temperature_f == 65.3


def test_wttrin_provider_fallback():
    provider = WttrInProvider()
    report = provider.fallback(city="Paris")
    assert report.location == "Paris"
    assert report.condition == "Overcast"


def test_custom_provider_fallback():
    provider = CustomEndpointsProvider()
    res = provider.fallback(urls=["https://example.com/api"])
    assert len(res) == 1
    assert res[0].url == "https://example.com/api"
    assert res[0].status_code == 200


def test_provider_health_tracking():
    provider = HackerNewsProvider()
    assert provider.get_health().is_healthy is True

    provider.record_failure(50.0)
    health = provider.get_health()
    assert health.is_healthy is False
    assert health.consecutive_failures == 1
    assert health.error_count == 1

    provider.record_success(15.0)
    health_recovered = provider.get_health()
    assert health_recovered.is_healthy is True
    assert health_recovered.consecutive_failures == 0
    assert health_recovered.success_count == 1
