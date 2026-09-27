from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from autoflow.models.db_models import Workflow, WorkflowRun, WorkflowStep
from autoflow.models.enums import TriggerType
from autoflow.models.schemas import WorkflowCreate, WorkflowUpdate


class WorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, schema: WorkflowCreate) -> Workflow:
        workflow = Workflow(
            name=schema.name,
            description=schema.description,
            enabled=schema.enabled,
            trigger_type=schema.trigger_type.value if hasattr(schema.trigger_type, "value") else str(schema.trigger_type),
            trigger_config=schema.trigger_config,
            conditions=[c.model_dump() for c in schema.conditions],
        )
        self.session.add(workflow)
        await self.session.flush()

        for idx, step_schema in enumerate(schema.steps):
            step = WorkflowStep(
                workflow_id=workflow.id,
                step_order=step_schema.step_order if step_schema.step_order != 0 else idx,
                step_name=step_schema.step_name,
                action_type=step_schema.action_type,
                action_config=step_schema.action_config,
                continue_on_error=step_schema.continue_on_error,
                retry_count=step_schema.retry_count,
                retry_delay_seconds=step_schema.retry_delay_seconds,
            )
            self.session.add(step)

        await self.session.flush()
        await self.session.refresh(workflow, attribute_names=["steps"])
        return workflow

    async def get_by_id(self, workflow_id: str) -> Optional[Workflow]:
        stmt = (
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.id == workflow_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_all(
        self,
        trigger_type: Optional[str] = None,
        enabled_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Workflow]:
        stmt = (
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .order_by(Workflow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if trigger_type:
            stmt = stmt.where(Workflow.trigger_type == trigger_type)
        if enabled_only:
            stmt = stmt.where(Workflow.enabled.is_(True))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_with_counts(self) -> list[dict]:
        workflows = await self.list_all()
        items = []
        for wf in workflows:
            runs_count_stmt = select(func.count(WorkflowRun.id)).where(WorkflowRun.workflow_id == wf.id)
            runs_res = await self.session.execute(runs_count_stmt)
            runs_count = runs_res.scalar() or 0

            items.append({
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "enabled": wf.enabled,
                "trigger_type": wf.trigger_type,
                "created_at": wf.created_at,
                "updated_at": wf.updated_at,
                "steps_count": len(wf.steps),
                "runs_count": runs_count,
            })
        return items

    async def update(self, workflow_id: str, schema: WorkflowUpdate) -> Optional[Workflow]:
        workflow = await self.get_by_id(workflow_id)
        if not workflow:
            return None

        if schema.name is not None:
            workflow.name = schema.name
        if schema.description is not None:
            workflow.description = schema.description
        if schema.enabled is not None:
            workflow.enabled = schema.enabled
        if schema.trigger_type is not None:
            workflow.trigger_type = schema.trigger_type.value if hasattr(schema.trigger_type, "value") else str(schema.trigger_type)
        if schema.trigger_config is not None:
            workflow.trigger_config = schema.trigger_config
        if schema.conditions is not None:
            workflow.conditions = [c.model_dump() for c in schema.conditions]

        if schema.steps is not None:
            for existing_step in workflow.steps:
                await self.session.delete(existing_step)
            await self.session.flush()

            for idx, step_schema in enumerate(schema.steps):
                step = WorkflowStep(
                    workflow_id=workflow.id,
                    step_order=step_schema.step_order if step_schema.step_order != 0 else idx,
                    step_name=step_schema.step_name,
                    action_type=step_schema.action_type,
                    action_config=step_schema.action_config,
                    continue_on_error=step_schema.continue_on_error,
                    retry_count=step_schema.retry_count,
                    retry_delay_seconds=step_schema.retry_delay_seconds,
                )
                self.session.add(step)

        workflow.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(workflow, attribute_names=["steps"])
        return workflow

    async def delete(self, workflow_id: str) -> bool:
        workflow = await self.get_by_id(workflow_id)
        if not workflow:
            return False
        await self.session.delete(workflow)
        await self.session.flush()
        return True

    async def toggle(self, workflow_id: str) -> Optional[Workflow]:
        workflow = await self.get_by_id(workflow_id)
        if not workflow:
            return None
        workflow.enabled = not workflow.enabled
        workflow.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return workflow

    async def get_active_event_workflows(self, event_name: str) -> list[Workflow]:
        workflows = await self.list_all(trigger_type=TriggerType.EVENT.value, enabled_only=True)
        matched = []
        for wf in workflows:
            target_event = wf.trigger_config.get("event_name")
            if target_event == event_name or target_event == "*":
                matched.append(wf)
        return matched

    async def get_active_scheduled_workflows(self) -> list[Workflow]:
        return await self.list_all(trigger_type=TriggerType.SCHEDULE.value, enabled_only=True)
