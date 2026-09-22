from typing import Optional
from fastapi import APIRouter, Depends, Query
from flagforge.dependencies import get_audit_repo
from flagforge.models.common import PaginatedResponse, PaginationMeta
from flagforge.models.audit import AuditLogEntry
from flagforge.repositories.memory import InMemoryAuditRepository

router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit"])


@router.get("", response_model=PaginatedResponse[AuditLogEntry])
async def list_audit_logs(
    flag_key: Optional[str] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    audit_repo: InMemoryAuditRepository = Depends(get_audit_repo),
):
    entries, total = await audit_repo.list(flag_key=flag_key, limit=limit, offset=offset)
    has_more = (offset + limit) < total
    return PaginatedResponse(
        items=entries,
        pagination=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more,
        ),
    )
