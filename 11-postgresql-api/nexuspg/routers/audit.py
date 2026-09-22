from typing import Optional
from fastapi import APIRouter, Depends, Query
from nexuspg.core.errors import EntityNotFoundError
from nexuspg.dependencies import get_audit_repo, get_project_repo
from nexuspg.repositories.audit_repo import AuditRepository
from nexuspg.repositories.project_repo import ProjectRepository
from nexuspg.schemas.audit import AuditLogResponse
from nexuspg.schemas.common import PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    project_key: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    project_repo: ProjectRepository = Depends(get_project_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project_id = None
    if project_key:
        project = await project_repo.get_by_key(project_key)
        if not project:
            raise EntityNotFoundError("Project", project_key)
        project_id = project.id

    logs, total = await audit_repo.list(
        project_id=project_id,
        entity_type=entity_type,
        offset=offset,
        limit=limit,
    )
    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        ),
    )
