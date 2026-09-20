from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional
from fastapi import FastAPI, Query, status
from fastapi.responses import JSONResponse

from api_aggregator.config import CONFIG
from api_aggregator.engine import AggregationEngine
from api_aggregator.models import (
    AggregationMetrics,
    CustomEndpointRequest,
    CustomEndpointResult,
    UnifiedCryptoRate,
    UnifiedEnvelope,
    UnifiedNewsItem,
    UnifiedOverview,
    UnifiedWeatherReport,
)

engine = AggregationEngine()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.close()


app = FastAPI(
    title=CONFIG.app_name,
    version=CONFIG.app_version,
    lifespan=lifespan,
)


@app.get("/", tags=["Info"])
async def root() -> dict[str, Any]:
    return {
        "service": CONFIG.app_name,
        "version": CONFIG.app_version,
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/metrics",
            "/api/v1/aggregate/news",
            "/api/v1/aggregate/crypto",
            "/api/v1/aggregate/weather",
            "/api/v1/aggregate/overview",
            "/api/v1/aggregate/custom",
            "/api/v1/cache",
        ],
    }


@app.get("/health", tags=["Monitoring"])
async def health_check() -> dict[str, Any]:
    health_map = engine.get_provider_health_map()
    all_healthy = all(h.is_healthy for h in health_map.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "providers": {k: v.model_dump() for k, v in health_map.items()},
    }


@app.get("/metrics", response_model=AggregationMetrics, tags=["Monitoring"])
async def get_metrics() -> AggregationMetrics:
    return await engine.get_metrics()


@app.get(
    "/api/v1/aggregate/news",
    response_model=UnifiedEnvelope[list[UnifiedNewsItem]],
    tags=["Aggregation"],
)
async def get_aggregated_news(
    limit: int = Query(default=10, ge=1, le=50),
    use_cache: bool = Query(default=True),
    force_mock: bool = Query(default=False),
) -> UnifiedEnvelope[list[UnifiedNewsItem]]:
    return await engine.aggregate_news(
        limit=limit, use_cache=use_cache, force_mock=force_mock
    )


@app.get(
    "/api/v1/aggregate/crypto",
    response_model=UnifiedEnvelope[list[UnifiedCryptoRate]],
    tags=["Aggregation"],
)
async def get_aggregated_crypto(
    symbols: Optional[str] = Query(default="BTC,ETH,SOL"),
    use_cache: bool = Query(default=True),
    force_mock: bool = Query(default=False),
) -> UnifiedEnvelope[list[UnifiedCryptoRate]]:
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else ["BTC", "ETH", "SOL"]
    return await engine.aggregate_crypto(
        symbols=sym_list, use_cache=use_cache, force_mock=force_mock
    )


@app.get(
    "/api/v1/aggregate/weather",
    response_model=UnifiedEnvelope[Optional[UnifiedWeatherReport]],
    tags=["Aggregation"],
)
async def get_aggregated_weather(
    city: str = Query(default="London"),
    latitude: Optional[float] = Query(default=None),
    longitude: Optional[float] = Query(default=None),
    use_cache: bool = Query(default=True),
    force_mock: bool = Query(default=False),
) -> UnifiedEnvelope[Optional[UnifiedWeatherReport]]:
    return await engine.aggregate_weather(
        city=city,
        latitude=latitude,
        longitude=longitude,
        use_cache=use_cache,
        force_mock=force_mock,
    )


@app.get(
    "/api/v1/aggregate/overview",
    response_model=UnifiedEnvelope[UnifiedOverview],
    tags=["Aggregation"],
)
async def get_aggregated_overview(
    use_cache: bool = Query(default=True),
    force_mock: bool = Query(default=False),
) -> UnifiedEnvelope[UnifiedOverview]:
    return await engine.aggregate_overview(
        use_cache=use_cache, force_mock=force_mock
    )


@app.post(
    "/api/v1/aggregate/custom",
    response_model=UnifiedEnvelope[list[CustomEndpointResult]],
    tags=["Aggregation"],
)
async def post_custom_fanout(
    request: CustomEndpointRequest,
    force_mock: bool = Query(default=False),
) -> UnifiedEnvelope[list[CustomEndpointResult]]:
    return await engine.aggregate_custom(
        urls=request.urls,
        headers=request.headers,
        timeout_seconds=request.timeout_seconds,
        force_mock=force_mock,
    )


@app.delete("/api/v1/cache", tags=["Cache"])
async def clear_cache() -> JSONResponse:
    await engine.cache.clear()
    return JSONResponse(
        content={"status": "cleared", "message": "Cache successfully emptied."},
        status_code=status.HTTP_200_OK,
    )
