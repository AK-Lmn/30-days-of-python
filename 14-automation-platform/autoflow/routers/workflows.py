from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from autoflow.database import get_db
from autoflow.engine.executor import WorkflowExecutor
from autoflow.models.enums import TriggerType
from autoflow.models.schemas import (
    RunTriggerRequest,
    WorkflowCreate,
    WorkflowListItem,
    WorkflowRead,
    WorkflowRunRead,
    WorkflowUpdate,
)
from autoflow.repositories.workflow_repo import WorkflowRepository

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    session: AsyncSession = Depends(get_db),
) -> WorkflowRead:
    repo = WorkflowRepository(session)
    workflow = await repo.create(payload)
    return WorkflowRead.model_validate(workflow)


@router.get("", response_model=list[WorkflowListItem])
async def list_workflows(
    session: AsyncSession = Depends(get_db),
) -> list[WorkflowListItem]:
    repo = WorkflowRepository(session)
    items = await repo.list_with_counts()
    return [WorkflowListItem.model_validate(item) for item in items]


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
) -> WorkflowRead:
    repo = WorkflowRepository(session)
    workflow = await repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowRead.model_validate(workflow)


@router.put("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    session: AsyncSession = Depends(get_db),
) -> WorkflowRead:
    repo = WorkflowRepository(session)
    workflow = await repo.update(workflow_id, payload)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowRead.model_validate(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
) -> None:
    repo = WorkflowRepository(session)
    deleted = await repo.delete(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/{workflow_id}/toggle", response_model=WorkflowRead)
async def toggle_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
) -> WorkflowRead:
    repo = WorkflowRepository(session)
    workflow = await repo.toggle(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowRead.model_validate(workflow)


@router.post("/{workflow_id}/run", response_model=WorkflowRunRead)
async def trigger_workflow_run(
    workflow_id: str,
    payload: Optional[RunTriggerRequest] = None,
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunRead:
    repo = WorkflowRepository(session)
    workflow = await repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    trigger_payload = payload.payload if payload else {}
    executor = WorkflowExecutor(session)
    run = await executor.execute_workflow(
        workflow=workflow,
        trigger_type=TriggerType.MANUAL.value,
        trigger_payload=trigger_payload,
    )
    return WorkflowRunRead.model_validate(run)
