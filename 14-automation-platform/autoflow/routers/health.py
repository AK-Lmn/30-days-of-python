from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoflow.config import get_settings
from autoflow.database import get_db
from autoflow.models.db_models import Workflow, WorkflowRun
from autoflow.models.enums import RunStatus
from autoflow.models.schemas import HealthResponse, PlatformStats
from autoflow.repositories.run_repo import RunRepository

router = APIRouter(tags=["Health & Stats"])


@router.get("/health", response_model=HealthResponse)
@router.get("/api/v1/health", response_model=HealthResponse)
async def get_health(session: AsyncSession = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    total_wf = await session.execute(select(func.count(Workflow.id)))
    active_runs = await session.execute(
        select(func.count(WorkflowRun.id)).where(WorkflowRun.status == RunStatus.RUNNING.value)
    )
    return HealthResponse(
        status="healthy",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        total_workflows=total_wf.scalar() or 0,
        active_runs=active_runs.scalar() or 0,
    )


@router.get("/api/v1/stats", response_model=PlatformStats)
async def get_stats(session: AsyncSession = Depends(get_db)) -> PlatformStats:
    repo = RunRepository(session)
    data = await repo.get_stats()
    return PlatformStats.model_validate(data)
