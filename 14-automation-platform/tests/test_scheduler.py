from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from autoflow.engine.scheduler import WorkflowScheduler
from autoflow.models.enums import TriggerType
from autoflow.models.schemas import StepCreate, WorkflowCreate
from autoflow.repositories.workflow_repo import WorkflowRepository


@pytest.mark.asyncio
async def test_scheduler_is_due_interval(session_factory):
    scheduler = WorkflowScheduler(session_factory=session_factory, interval_seconds=1.0)
    now = datetime.now(timezone.utc)

    config = {"interval_seconds": 10}
    assert await scheduler.is_due("wf-1", config, now) is True

    scheduler._last_runs["wf-1"] = now
    assert await scheduler.is_due("wf-1", config, now) is False


@pytest.mark.asyncio
async def test_scheduler_is_due_cron(session_factory):
    scheduler = WorkflowScheduler(session_factory=session_factory, interval_seconds=1.0)
    now = datetime.now(timezone.utc)

    config = {"cron": "* * * * *"}
    assert await scheduler.is_due("wf-cron", config, now) is True

    scheduler._last_runs["wf-cron"] = now
    assert await scheduler.is_due("wf-cron", config, now) is False


@pytest.mark.asyncio
async def test_scheduler_tick(session_factory):
    async with session_factory() as session:
        repo = WorkflowRepository(session)
        wf_schema = WorkflowCreate(
            name="Scheduled Test Automation",
            enabled=True,
            trigger_type=TriggerType.SCHEDULE,
            trigger_config={"interval_seconds": 1},
            steps=[
                StepCreate(
                    step_order=0,
                    step_name="tick_step",
                    action_type="notification",
                    action_config={"recipient": "tick@example.com", "message": "ping"},
                )
            ],
        )
        wf = await repo.create(wf_schema)
        await session.commit()
        workflow_id = wf.id

    scheduler = WorkflowScheduler(session_factory=session_factory, interval_seconds=1.0)
    triggered = await scheduler.tick()

    assert workflow_id in triggered
