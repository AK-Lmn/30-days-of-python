from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from autoflow.database import get_db
from autoflow.engine.executor import WorkflowExecutor
from autoflow.models.enums import TriggerType
from autoflow.models.schemas import EventIngestRequest, EventIngestResponse, EventLogRead
from autoflow.repositories.run_repo import RunRepository
from autoflow.repositories.workflow_repo import WorkflowRepository

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    event_data: EventIngestRequest,
    session: AsyncSession = Depends(get_db),
) -> EventIngestResponse:
    wf_repo = WorkflowRepository(session)
    run_repo = RunRepository(session)

    matched_workflows = await wf_repo.get_active_event_workflows(event_data.event_name)
    event_log = await run_repo.record_event(
        event_name=event_data.event_name,
        payload=event_data.payload,
        matched_count=len(matched_workflows),
    )

    runs_triggered: list[str] = []
    executor = WorkflowExecutor(session)

    for wf in matched_workflows:
        run = await executor.execute_workflow(
            workflow=wf,
            trigger_type=TriggerType.EVENT.value,
            trigger_payload=event_data.payload,
        )
        runs_triggered.append(run.id)

    return EventIngestResponse(
        event_id=event_log.id,
        event_name=event_log.event_name,
        matched_workflows=[wf.id for wf in matched_workflows],
        runs_triggered=runs_triggered,
        received_at=event_log.received_at,
    )


@router.get("", response_model=list[EventLogRead])
async def list_events(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[EventLogRead]:
    repo = RunRepository(session)
    events = await repo.list_events(limit=limit, offset=offset)
    return [EventLogRead.model_validate(e) for e in events]
