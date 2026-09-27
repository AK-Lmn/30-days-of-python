from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from taskforge.database import get_db
from taskforge.models.schemas import WorkerResponse
from taskforge.repositories.job_repo import JobRepository

router = APIRouter(prefix="/workers", tags=["Workers"])


@router.get("", response_model=list[WorkerResponse])
async def list_active_workers(
    active_within_seconds: float = Query(default=30.0, ge=1.0),
    session: AsyncSession = Depends(get_db),
) -> list[WorkerResponse]:
    repo = JobRepository(session)
    workers = await repo.list_workers(active_within_seconds=active_within_seconds)
    response = []
    for w in workers:
        response.append(
            WorkerResponse(
                id=w.id,
                hostname=w.hostname,
                pid=w.pid,
                queues=w.queues.split(",") if w.queues else [],
                concurrency=w.concurrency,
                status=w.status,
                current_job_id=w.current_job_id,
                jobs_completed=w.jobs_completed,
                jobs_failed=w.jobs_failed,
                last_heartbeat_at=w.last_heartbeat_at,
                started_at=w.started_at,
            )
        )
    return response
