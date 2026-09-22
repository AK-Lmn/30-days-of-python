from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from flagforge.core.errors import FlagNotFoundError, FlagAlreadyExistsError
from flagforge.dependencies import get_flag_repo, get_audit_repo
from flagforge.models.common import PaginatedResponse, PaginationMeta
from flagforge.models.flag import FlagCreate, FlagResponse, FlagUpdate, FlagToggleRequest
from flagforge.models.audit import AuditLogEntry, AuditAction
from flagforge.repositories.memory import InMemoryFlagRepository, InMemoryAuditRepository

router = APIRouter(prefix="/api/v1/flags", tags=["Flags"])


@router.get("", response_model=PaginatedResponse[FlagResponse])
async def list_flags(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    tag: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    enabled: Optional[bool] = Query(default=None),
    flag_repo: InMemoryFlagRepository = Depends(get_flag_repo),
):
    items, total = await flag_repo.list(
        offset=offset,
        limit=limit,
        tag=tag,
        search=search,
        enabled=enabled,
    )
    has_more = (offset + limit) < total
    return PaginatedResponse(
        items=items,
        pagination=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more,
        ),
    )


@router.post("", response_model=FlagResponse, status_code=status.HTTP_201_CREATED)
async def create_flag(
    flag_in: FlagCreate,
    flag_repo: InMemoryFlagRepository = Depends(get_flag_repo),
    audit_repo: InMemoryAuditRepository = Depends(get_audit_repo),
):
    try:
        created = await flag_repo.create(flag_in)
    except FlagAlreadyExistsError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err.message)

    await audit_repo.record(
        AuditLogEntry(
            flag_key=created.key,
            action=AuditAction.CREATED,
            diff={"created": created.model_dump(mode="json")},
        )
    )
    return created


@router.get("/{key}", response_model=FlagResponse)
async def get_flag(
    key: str,
    flag_repo: InMemoryFlagRepository = Depends(get_flag_repo),
):
    flag = await flag_repo.get(key)
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag with key '{key}' does not exist",
        )
    return flag


@router.put("/{key}", response_model=FlagResponse)
async def update_flag(
    key: str,
    update_data: FlagUpdate,
    flag_repo: InMemoryFlagRepository = Depends(get_flag_repo),
    audit_repo: InMemoryAuditRepository = Depends(get_audit_repo),
):
    try:
        updated = await flag_repo.update(key, update_data)
    except FlagNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message)

    await audit_repo.record(
        AuditLogEntry(
            flag_key=key,
            action=AuditAction.UPDATED,
            diff={"updated": update_data.model_dump(exclude_unset=True, mode="json")},
        )
    )
    return updated


@router.patch("/{key}/toggle", response_model=FlagResponse)
async def toggle_flag(
    key: str,
    toggle_req: Optional[FlagToggleRequest] = None,
    flag_repo: InMemoryFlagRepository = Depends(get_flag_repo),
    audit_repo: InMemoryAuditRepository = Depends(get_audit_repo),
):
    existing = await flag_repo.get(key)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag with key '{key}' does not exist",
        )

    new_enabled = (not existing.enabled) if (toggle_req is None or toggle_req.enabled is None) else toggle_req.enabled
    updated = await flag_repo.update(key, FlagUpdate(enabled=new_enabled))

    await audit_repo.record(
        AuditLogEntry(
            flag_key=key,
            action=AuditAction.TOGGLED,
            diff={"previous_state": existing.enabled, "new_state": new_enabled},
        )
    )
    return updated


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flag(
    key: str,
    flag_repo: InMemoryFlagRepository = Depends(get_flag_repo),
    audit_repo: InMemoryAuditRepository = Depends(get_audit_repo),
):
    try:
        await flag_repo.delete(key)
    except FlagNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message)

    await audit_repo.record(
        AuditLogEntry(
            flag_key=key,
            action=AuditAction.DELETED,
            diff={"deleted_key": key},
        )
    )
    return None
