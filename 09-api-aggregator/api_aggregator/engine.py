import asyncio
import time
from typing import Any, Optional
from api_aggregator.cache import AsyncCache
from api_aggregator.client import ResilientHttpClient
from api_aggregator.config import CONFIG
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
from api_aggregator.rate_limiter import RateLimiter


class AggregationEngine:
    def __init__(
        self,
        client: Optional[ResilientHttpClient] = None,
        cache: Optional[AsyncCache] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self.client = client or ResilientHttpClient()
        self.cache = cache or AsyncCache(
            max_size=CONFIG.cache_max_size,
            default_ttl=CONFIG.default_cache_ttl_seconds,
        )
        self.rate_limiter = rate_limiter or RateLimiter(
            rate=CONFIG.rate_limiter_rate,
            capacity=CONFIG.rate_limiter_capacity,
        )

        self.news_providers = [
            HackerNewsProvider(),
            GitHubEventsProvider(),
            DevToProvider(),
        ]
        self.crypto_providers = [
            CoinGeckoProvider(),
            CoinbaseProvider(),
            BinanceProvider(),
        ]
        self.weather_providers = [
            OpenMeteoProvider(),
            WttrInProvider(),
        ]
        self.custom_provider = CustomEndpointsProvider()

        self.total_requests = 0
        self.total_latency_ms = 0.0

    async def _execute_provider_task(
        self,
        provider: Any,
        force_mock: bool = False,
        **kwargs: Any,
    ) -> tuple[str, bool, Any, float]:
        start = time.perf_counter()
        provider_name = getattr(provider, "name", "unknown")

        if force_mock:
            data = provider.fallback(**kwargs)
            latency = round((time.perf_counter() - start) * 1000.0, 2)
            provider.record_success(latency)
            return provider_name, True, data, latency

        try:
            await self.rate_limiter.wait_and_acquire(tokens=1.0, timeout=1.5)
            data = await provider.fetch(self.client, **kwargs)
            latency = round((time.perf_counter() - start) * 1000.0, 2)
            provider.record_success(latency)
            return provider_name, True, data, latency
        except Exception:
            latency = round((time.perf_counter() - start) * 1000.0, 2)
            provider.record_failure(latency)
            try:
                fallback_data = provider.fallback(**kwargs)
                return provider_name, True, fallback_data, latency
            except Exception as fb_exc:
                return provider_name, False, str(fb_exc), latency

    async def aggregate_news(
        self,
        limit: int = 10,
        use_cache: bool = True,
        force_mock: bool = False,
    ) -> UnifiedEnvelope[list[UnifiedNewsItem]]:
        cache_key = f"news:limit={limit}:mock={force_mock}"
        if use_cache:
            cached_res = await self.cache.get(cache_key)
            if cached_res is not None:
                envelope = cached_res.model_copy()
                envelope.cached = True
                return envelope

        start = time.perf_counter()
        tasks = [
            self._execute_provider_task(p, force_mock=force_mock, limit=limit)
            for p in self.news_providers
            if p.enabled
        ]
        results = await asyncio.gather(*tasks)

        sources_queried: list[str] = []
        sources_succeeded: list[str] = []
        sources_failed: list[str] = []
        all_items: list[UnifiedNewsItem] = []

        for name, success, data, _ in results:
            sources_queried.append(name)
            if success and isinstance(data, list):
                sources_succeeded.append(name)
                all_items.extend(data)
            else:
                sources_failed.append(name)

        seen_titles = set()
        deduped: list[UnifiedNewsItem] = []
        for item in all_items:
            clean_title = item.title.strip().lower()
            if clean_title not in seen_titles:
                seen_titles.add(clean_title)
                deduped.append(item)

        deduped.sort(key=lambda x: x.score, reverse=True)
        final_items = deduped[:limit]

        latency = round((time.perf_counter() - start) * 1000.0, 2)
        self.total_requests += 1
        self.total_latency_ms += latency

        status = (
            AggregateStatus.SUCCESS
            if len(sources_failed) == 0
            else (
                AggregateStatus.PARTIAL
                if len(sources_succeeded) > 0
                else AggregateStatus.ERROR
            )
        )

        envelope = UnifiedEnvelope[list[UnifiedNewsItem]](
            status=status,
            latency_ms=latency,
            sources_queried=sources_queried,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            cached=False,
            count=len(final_items),
            data=final_items,
        )

        if use_cache:
            await self.cache.set(cache_key, envelope)

        return envelope

    async def aggregate_crypto(
        self,
        symbols: list[str] | None = None,
        use_cache: bool = True,
        force_mock: bool = False,
    ) -> UnifiedEnvelope[list[UnifiedCryptoRate]]:
        target_symbols = [s.upper() for s in (symbols or ["BTC", "ETH", "SOL"])]
        cache_key = f"crypto:syms={','.join(sorted(target_symbols))}:mock={force_mock}"
        if use_cache:
            cached_res = await self.cache.get(cache_key)
            if cached_res is not None:
                envelope = cached_res.model_copy()
                envelope.cached = True
                return envelope

        start = time.perf_counter()
        tasks = [
            self._execute_provider_task(
                p, force_mock=force_mock, symbols=target_symbols
            )
            for p in self.crypto_providers
            if p.enabled
        ]
        results = await asyncio.gather(*tasks)

        sources_queried: list[str] = []
        sources_succeeded: list[str] = []
        sources_failed: list[str] = []

        symbol_buckets: dict[str, list[UnifiedCryptoRate]] = {
            s: [] for s in target_symbols
        }

        for name, success, data, _ in results:
            sources_queried.append(name)
            if success and isinstance(data, list):
                sources_succeeded.append(name)
                for rate in data:
                    if rate.symbol in symbol_buckets:
                        symbol_buckets[rate.symbol].append(rate)
            else:
                sources_failed.append(name)

        reconciled_rates: list[UnifiedCryptoRate] = []
        for sym, rates in symbol_buckets.items():
            if not rates:
                continue
            prices = [r.price_usd for r in rates if r.price_usd > 0]
            avg_price = round(sum(prices) / len(prices), 2) if prices else 0.0

            min_price = min(prices) if prices else 0.0
            max_price = max(prices) if prices else 0.0
            discrepancy = (
                round(((max_price - min_price) / min_price) * 100.0, 2)
                if min_price > 0
                else 0.0
            )

            all_sources = sorted(
                list(
                    {
                        src
                        for r in rates
                        for src in r.sources
                    }
                )
            )

            primary = rates[0]
            name = primary.name
            change_24h = primary.change_24h_percent
            mcap = next((r.market_cap for r in rates if r.market_cap is not None), None)
            vol = next((r.volume_24h for r in rates if r.volume_24h is not None), None)
            high_24h = next((r.high_24h for r in rates if r.high_24h is not None), None)
            low_24h = next((r.low_24h for r in rates if r.low_24h is not None), None)

            reconciled_rates.append(
                UnifiedCryptoRate(
                    symbol=sym,
                    name=name,
                    price_usd=avg_price,
                    change_24h_percent=change_24h,
                    high_24h=high_24h,
                    low_24h=low_24h,
                    volume_24h=vol,
                    market_cap=mcap,
                    sources=all_sources,
                    discrepancy_percent=discrepancy,
                )
            )

        latency = round((time.perf_counter() - start) * 1000.0, 2)
        self.total_requests += 1
        self.total_latency_ms += latency

        status = (
            AggregateStatus.SUCCESS
            if len(sources_failed) == 0
            else (
                AggregateStatus.PARTIAL
                if len(sources_succeeded) > 0
                else AggregateStatus.ERROR
            )
        )

        envelope = UnifiedEnvelope[list[UnifiedCryptoRate]](
            status=status,
            latency_ms=latency,
            sources_queried=sources_queried,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            cached=False,
            count=len(reconciled_rates),
            data=reconciled_rates,
        )

        if use_cache:
            await self.cache.set(cache_key, envelope)

        return envelope

    async def aggregate_weather(
        self,
        city: str = "London",
        latitude: float | None = None,
        longitude: float | None = None,
        use_cache: bool = True,
        force_mock: bool = False,
    ) -> UnifiedEnvelope[Optional[UnifiedWeatherReport]]:
        cache_key = f"weather:city={city}:lat={latitude}:lon={longitude}:mock={force_mock}"
        if use_cache:
            cached_res = await self.cache.get(cache_key)
            if cached_res is not None:
                envelope = cached_res.model_copy()
                envelope.cached = True
                return envelope

        start = time.perf_counter()
        tasks = [
            self._execute_provider_task(
                p,
                force_mock=force_mock,
                city=city,
                latitude=latitude,
                longitude=longitude,
            )
            for p in self.weather_providers
            if p.enabled
        ]
        results = await asyncio.gather(*tasks)

        sources_queried: list[str] = []
        sources_succeeded: list[str] = []
        sources_failed: list[str] = []
        reports: list[UnifiedWeatherReport] = []

        for name, success, data, _ in results:
            sources_queried.append(name)
            if success and isinstance(data, UnifiedWeatherReport):
                sources_succeeded.append(name)
                reports.append(data)
            else:
                sources_failed.append(name)

        final_report: Optional[UnifiedWeatherReport] = None
        if reports:
            primary = reports[0]
            all_sources = sorted(
                list({src for r in reports for src in r.sources})
            )
            final_report = UnifiedWeatherReport(
                location=primary.location,
                latitude=primary.latitude,
                longitude=primary.longitude,
                temperature_c=primary.temperature_c,
                temperature_f=primary.temperature_f,
                humidity_percent=primary.humidity_percent,
                wind_speed_kmh=primary.wind_speed_kmh,
                condition=primary.condition,
                sources=all_sources,
                timestamp=primary.timestamp,
            )

        latency = round((time.perf_counter() - start) * 1000.0, 2)
        self.total_requests += 1
        self.total_latency_ms += latency

        status = (
            AggregateStatus.SUCCESS
            if len(sources_failed) == 0 and final_report is not None
            else (
                AggregateStatus.PARTIAL
                if final_report is not None
                else AggregateStatus.ERROR
            )
        )

        envelope = UnifiedEnvelope[Optional[UnifiedWeatherReport]](
            status=status,
            latency_ms=latency,
            sources_queried=sources_queried,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            cached=False,
            count=1 if final_report is not None else 0,
            data=final_report,
        )

        if use_cache and final_report is not None:
            await self.cache.set(cache_key, envelope)

        return envelope

    async def aggregate_overview(
        self,
        use_cache: bool = True,
        force_mock: bool = False,
    ) -> UnifiedEnvelope[UnifiedOverview]:
        cache_key = f"overview:mock={force_mock}"
        if use_cache:
            cached_res = await self.cache.get(cache_key)
            if cached_res is not None:
                envelope = cached_res.model_copy()
                envelope.cached = True
                return envelope

        start = time.perf_counter()
        news_res, crypto_res, weather_res = await asyncio.gather(
            self.aggregate_news(limit=5, use_cache=False, force_mock=force_mock),
            self.aggregate_crypto(
                symbols=["BTC", "ETH", "SOL"], use_cache=False, force_mock=force_mock
            ),
            self.aggregate_weather(
                city="San Francisco", use_cache=False, force_mock=force_mock
            ),
        )

        sources_queried = sorted(
            list(
                set(
                    news_res.sources_queried
                    + crypto_res.sources_queried
                    + weather_res.sources_queried
                )
            )
        )
        sources_succeeded = sorted(
            list(
                set(
                    news_res.sources_succeeded
                    + crypto_res.sources_succeeded
                    + weather_res.sources_succeeded
                )
            )
        )
        sources_failed = sorted(
            list(
                set(
                    news_res.sources_failed
                    + crypto_res.sources_failed
                    + weather_res.sources_failed
                )
            )
        )

        latency = round((time.perf_counter() - start) * 1000.0, 2)
        overview_data = UnifiedOverview(
            timestamp=news_res.timestamp,
            news_count=len(news_res.data),
            top_news=news_res.data,
            crypto_rates=crypto_res.data,
            weather=weather_res.data,
            latency_ms=latency,
        )

        envelope = UnifiedEnvelope[UnifiedOverview](
            status=(
                AggregateStatus.SUCCESS
                if not sources_failed
                else AggregateStatus.PARTIAL
            ),
            latency_ms=latency,
            sources_queried=sources_queried,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            cached=False,
            count=1,
            data=overview_data,
        )

        if use_cache:
            await self.cache.set(cache_key, envelope, ttl=60.0)

        return envelope

    async def aggregate_custom(
        self,
        urls: list[str],
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 5.0,
        force_mock: bool = False,
    ) -> UnifiedEnvelope[list[CustomEndpointResult]]:
        start = time.perf_counter()
        _, success, data, _ = await self._execute_provider_task(
            self.custom_provider,
            force_mock=force_mock,
            urls=urls,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )

        latency = round((time.perf_counter() - start) * 1000.0, 2)
        results = data if isinstance(data, list) else []

        succeeded = [r.url for r in results if r.error is None]
        failed = [r.url for r in results if r.error is not None]

        return UnifiedEnvelope[list[CustomEndpointResult]](
            status=AggregateStatus.SUCCESS if not failed else AggregateStatus.PARTIAL,
            latency_ms=latency,
            sources_queried=urls,
            sources_succeeded=succeeded,
            sources_failed=failed,
            cached=False,
            count=len(results),
            data=results,
        )

    def get_provider_health_map(self) -> dict[str, ProviderHealth]:
        providers = (
            self.news_providers
            + self.crypto_providers
            + self.weather_providers
            + [self.custom_provider]
        )
        health_map: dict[str, ProviderHealth] = {}
        circuit_breakers = self.client.get_all_circuit_breakers()

        for p in providers:
            health = p.get_health()
            cb = circuit_breakers.get(p.name)
            if cb:
                health.circuit_state = cb.state
            health_map[p.name] = health

        return health_map

    async def get_metrics(self) -> AggregationMetrics:
        avg_latency = (
            round(self.total_latency_ms / self.total_requests, 2)
            if self.total_requests > 0
            else 0.0
        )
        return AggregationMetrics(
            total_requests=self.total_requests,
            cache_hits=self.cache.hits,
            cache_misses=self.cache.misses,
            average_latency_ms=avg_latency,
            provider_stats=self.get_provider_health_map(),
        )

    async def close(self) -> None:
        await self.client.close()
