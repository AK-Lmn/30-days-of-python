from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from autoflow.models.db_models import EventLog, StepRun, Workflow, WorkflowRun
from autoflow.models.enums import RunStatus, StepStatus


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(
        self,
        workflow_id: str,
        trigger_type: str,
        trigger_payload: dict[str, Any],
    ) -> WorkflowRun:
        run = WorkflowRun(
            workflow_id=workflow_id,
            trigger_type=trigger_type,
            status=RunStatus.PENDING.value,
            trigger_payload=trigger_payload,
            context_data={},
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def update_run(
        self,
        run_id: str,
        status: Optional[str] = None,
        context_data: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[float] = None,
    ) -> Optional[WorkflowRun]:
        stmt = select(WorkflowRun).where(WorkflowRun.id == run_id)
        result = await self.session.execute(stmt)
        run = result.scalars().first()
        if not run:
            return None

        if status is not None:
            run.status = status
        if context_data is not None:
            run.context_data = context_data
        if error_message is not None:
            run.error_message = error_message
        if completed_at is not None:
            run.completed_at = completed_at
        if duration_ms is not None:
            run.duration_ms = duration_ms

        await self.session.flush()
        return run

    async def create_step_run(
        self,
        run_id: str,
        step_id: str,
        step_name: str,
        action_type: str,
        input_data: dict[str, Any],
        attempt: int = 1,
    ) -> StepRun:
        step_run = StepRun(
            run_id=run_id,
            step_id=step_id,
            step_name=step_name,
            action_type=action_type,
            status=StepStatus.RUNNING.value,
            input_data=input_data,
            output_data={},
            attempt=attempt,
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(step_run)
        await self.session.flush()
        return step_run

    async def update_step_run(
        self,
        step_run_id: str,
        status: str,
        output_data: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> Optional[StepRun]:
        stmt = select(StepRun).where(StepRun.id == step_run_id)
        result = await self.session.execute(stmt)
        step_run = result.scalars().first()
        if not step_run:
            return None

        step_run.status = status
        if output_data is not None:
            step_run.output_data = output_data
        if error_message is not None:
            step_run.error_message = error_message
        if duration_ms is not None:
            step_run.duration_ms = duration_ms
        step_run.completed_at = datetime.now(timezone.utc)

        await self.session.flush()
        return step_run

    async def get_run_by_id(self, run_id: str) -> Optional[WorkflowRun]:
        stmt = (
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.step_runs))
            .where(WorkflowRun.id == run_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_runs(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowRun]:
        stmt = (
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.step_runs))
            .order_by(WorkflowRun.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workflow_id:
            stmt = stmt.where(WorkflowRun.workflow_id == workflow_id)
        if status:
            stmt = stmt.where(WorkflowRun.status == status)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def record_event(self, event_name: str, payload: dict[str, Any], matched_count: int) -> EventLog:
        event = EventLog(
            event_name=event_name,
            payload=payload,
            matched_workflows_count=matched_count,
            received_at=datetime.now(timezone.utc),
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_events(self, limit: int = 50, offset: int = 0) -> list[EventLog]:
        stmt = (
            select(EventLog)
            .order_by(EventLog.received_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_stats(self) -> dict[str, int]:
        total_wf_res = await self.session.execute(select(func.count(Workflow.id)))
        active_wf_res = await self.session.execute(select(func.count(Workflow.id)).where(Workflow.enabled.is_(True)))
        total_runs_res = await self.session.execute(select(func.count(WorkflowRun.id)))
        succ_runs_res = await self.session.execute(
            select(func.count(WorkflowRun.id)).where(WorkflowRun.status == RunStatus.COMPLETED.value)
        )
        fail_runs_res = await self.session.execute(
            select(func.count(WorkflowRun.id)).where(WorkflowRun.status == RunStatus.FAILED.value)
        )
        events_res = await self.session.execute(select(func.count(EventLog.id)))

        return {
            "total_workflows": total_wf_res.scalar() or 0,
            "active_workflows": active_wf_res.scalar() or 0,
            "total_runs": total_runs_res.scalar() or 0,
            "successful_runs": succ_runs_res.scalar() or 0,
            "failed_runs": fail_runs_res.scalar() or 0,
            "total_events": events_res.scalar() or 0,
        }
