from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from taskforge.core.enums import ScheduleType
from taskforge.core.registry import registry
from taskforge.core.scheduler import Scheduler
from taskforge.database import get_db
from taskforge.models.schemas import ScheduleCreate, ScheduleResponse
from taskforge.repositories.job_repo import JobRepository

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreate,
    session: AsyncSession = Depends(get_db),
) -> ScheduleResponse:
    if not registry.has_task(payload.task_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task '{payload.task_name}' is not registered. Available: {registry.list_tasks()}",
        )

    try:
        next_run_at = Scheduler.calculate_next_run(
            schedule_type=payload.schedule_type,
            expression=payload.expression,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid schedule expression: {str(err)}",
        )

    repo = JobRepository(session)
    schedule = await repo.create_schedule(
        name=payload.name,
        task_name=payload.task_name,
        expression=payload.expression,
        queue=payload.queue,
        payload=payload.payload,
        priority=payload.priority,
        schedule_type=payload.schedule_type,
        next_run_at=next_run_at,
    )
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        task_name=schedule.task_name,
        queue=schedule.queue,
        payload=schedule.payload,
        priority=schedule.priority,
        schedule_type=ScheduleType(schedule.schedule_type),
        expression=schedule.expression,
        enabled=schedule.enabled,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    session: AsyncSession = Depends(get_db),
) -> list[ScheduleResponse]:
    repo = JobRepository(session)
    schedules = await repo.list_schedules()
    return [
        ScheduleResponse(
            id=s.id,
            name=s.name,
            task_name=s.task_name,
            queue=s.queue,
            payload=s.payload,
            priority=s.priority,
            schedule_type=ScheduleType(s.schedule_type),
            expression=s.expression,
            enabled=s.enabled,
            last_run_at=s.last_run_at,
            next_run_at=s.next_run_at,
            created_at=s.created_at,
        )
        for s in schedules
    ]


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: str,
    session: AsyncSession = Depends(get_db),
) -> None:
    repo = JobRepository(session)
    deleted = await repo.delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found",
        )
