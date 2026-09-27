from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from autoflow.database import get_db
from autoflow.models.enums import RunStatus
from autoflow.models.schemas import RunCancelResponse, WorkflowRunRead
from autoflow.repositories.run_repo import RunRepository

router = APIRouter(prefix="/runs", tags=["Workflow Runs"])


@router.get("", response_model=list[WorkflowRunRead])
async def list_runs(
    workflow_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[WorkflowRunRead]:
    repo = RunRepository(session)
    runs = await repo.list_runs(
        workflow_id=workflow_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [WorkflowRunRead.model_validate(r) for r in runs]


@router.get("/{run_id}", response_model=WorkflowRunRead)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunRead:
    repo = RunRepository(session)
    run = await repo.get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return WorkflowRunRead.model_validate(run)


@router.post("/{run_id}/cancel", response_model=RunCancelResponse)
async def cancel_run(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> RunCancelResponse:
    repo = RunRepository(session)
    run = await repo.get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status in (RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.SKIPPED.value):
        raise HTTPException(
            status_code=400,
            detail=f"Run has already finished with status '{run.status}'",
        )

    await repo.update_run(run_id=run.id, status=RunStatus.CANCELLED.value)
    return RunCancelResponse(
        id=run.id,
        status=RunStatus.CANCELLED.value,
        message="Workflow run cancelled successfully",
    )
