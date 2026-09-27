from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from taskforge.core.enums import JobStatus
from taskforge.core.exceptions import (
    InvalidJobStateError,
    JobAlreadyCancelledError,
    JobNotFoundError,
    TaskNotFoundError,
)
from taskforge.core.registry import registry
from taskforge.database import get_db
from taskforge.models.db_models import utc_now
from taskforge.models.schemas import (
    JobCancelResponse,
    JobCreate,
    JobListResponse,
    JobResponse,
    JobRetryResponse,
)
from taskforge.repositories.job_repo import JobRepository

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    session: AsyncSession = Depends(get_db),
) -> JobResponse:
    if not registry.has_task(payload.task_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task '{payload.task_name}' is not registered. Available: {registry.list_tasks()}",
        )

    scheduled_at = payload.scheduled_at
    if payload.delay_seconds > 0:
        scheduled_at = utc_now() + timedelta(seconds=payload.delay_seconds)

    repo = JobRepository(session)
    job = await repo.create_job(
        task_name=payload.task_name,
        payload=payload.payload,
        queue=payload.queue,
        priority=payload.priority,
        scheduled_at=scheduled_at,
        max_retries=payload.max_retries,
        retry_delay_seconds=payload.retry_delay_seconds,
        timeout_seconds=payload.timeout_seconds,
    )
    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    queue: str | None = Query(default=None),
    status: JobStatus | None = Query(default=None),
    task_name: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> JobListResponse:
    repo = JobRepository(session)
    items, total = await repo.list_jobs(
        queue=queue,
        status=status,
        task_name=task_name,
        offset=offset,
        limit=limit,
    )
    return JobListResponse(
        items=[JobResponse.model_validate(item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/registered-tasks", response_model=list[str])
async def list_registered_tasks() -> list[str]:
    return registry.list_tasks()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> JobResponse:
    repo = JobRepository(session)
    job = await repo.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )
    return JobResponse.model_validate(job)


@router.post("/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> JobCancelResponse:
    repo = JobRepository(session)
    try:
        job = await repo.cancel_job(job_id)
        return JobCancelResponse(
            id=job.id,
            status=JobStatus(job.status),
            message="Job cancelled successfully",
        )
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )
    except (JobAlreadyCancelledError, InvalidJobStateError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


@router.post("/{job_id}/retry", response_model=JobRetryResponse)
async def retry_job(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> JobRetryResponse:
    repo = JobRepository(session)
    try:
        job = await repo.retry_job(job_id)
        return JobRetryResponse(
            id=job.id,
            status=JobStatus(job.status),
            message="Job reset to pending status for retry",
        )
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )
    except InvalidJobStateError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )
