from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI
from hookrelay.api.routes import (
    deliveries_router,
    endpoints_router,
    events_router,
    ingest_router,
    subscriptions_router,
)
from hookrelay.config import settings
from hookrelay.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Webhook Ingestion, Verification, Storage, and Delivery Engine",
        lifespan=lifespan,
    )

    app.include_router(ingest_router)
    app.include_router(endpoints_router)
    app.include_router(subscriptions_router)
    app.include_router(events_router)
    app.include_router(deliveries_router)

    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

    return app


app = create_app()
