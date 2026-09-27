from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from taskforge.config import get_settings
from taskforge.database import async_session_factory, get_db, init_db
from taskforge.models.schemas import HealthResponse
from taskforge.repositories.job_repo import JobRepository
from taskforge.routers import jobs_router, queues_router, schedules_router, workers_router
import taskforge.tasks.builtins


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(queues_router, prefix="/api/v1")
    app.include_router(workers_router, prefix="/api/v1")
    app.include_router(schedules_router, prefix="/api/v1")

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    @app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
    async def health(session: AsyncSession = Depends(get_db)) -> HealthResponse:
        repo = JobRepository(session)
        workers = await repo.list_workers()
        queues = await repo.get_queue_stats()
        pending_count = sum(q.pending for q in queues)

        return HealthResponse(
            status="healthy",
            app=settings.app_name,
            version="0.1.0",
            environment=settings.environment,
            active_workers=len(workers),
            pending_jobs=pending_count,
        )

    return app


app = create_app()
