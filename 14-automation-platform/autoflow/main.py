from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from autoflow.config import get_settings
from autoflow.database import async_session_factory, init_db
from autoflow.engine.scheduler import WorkflowScheduler
from autoflow.routers import (
    actions_router,
    events_router,
    health_router,
    runs_router,
    workflows_router,
)


def create_app(enable_scheduler: bool = True) -> FastAPI:
    settings = get_settings()
    scheduler: WorkflowScheduler | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        nonlocal scheduler
        await init_db()
        if enable_scheduler:
            scheduler = WorkflowScheduler(
                session_factory=async_session_factory,
                interval_seconds=settings.scheduler_interval_seconds,
            )
            scheduler.start()
        yield
        if scheduler:
            await scheduler.stop()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(workflows_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(actions_router, prefix="/api/v1")

    return app


app = create_app(enable_scheduler=True)
