from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from nexuspg.core.errors import EntityNotFoundError
from nexuspg.dependencies import get_audit_repo, get_flag_repo, get_project_repo
from nexuspg.repositories.audit_repo import AuditRepository
from nexuspg.repositories.flag_repo import FlagRepository
from nexuspg.repositories.project_repo import ProjectRepository
from nexuspg.schemas.common import PaginatedResponse, PaginationMeta
from nexuspg.schemas.flag import (
    FlagCreate,
    FlagDetailResponse,
    FlagEnvironmentStateResponse,
    FlagEnvironmentStateUpdate,
    FlagResponse,
    FlagUpdate,
)

router = APIRouter(prefix="/projects/{project_key}/flags", tags=["Flags"])


@router.post("", response_model=FlagResponse, status_code=status.HTTP_201_CREATED)
async def create_flag(
    project_key: str,
    flag_in: FlagCreate,
    project_repo: ProjectRepository = Depends(get_project_repo),
    flag_repo: FlagRepository = Depends(get_flag_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    flag = await flag_repo.create(project.id, flag_in)
    await flag_repo.session.commit()
    await audit_repo.record(
        project_id=project.id,
        entity_type="flag",
        entity_id=str(flag.id),
        action="create",
        actor="system",
        changes=flag_in.model_dump(),
    )
    await flag_repo.session.commit()
    refreshed = await flag_repo.get_by_key(project.id, flag.key)
    return refreshed


@router.get("", response_model=PaginatedResponse[FlagResponse])
async def list_flags(
    project_key: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    project_repo: ProjectRepository = Depends(get_project_repo),
    flag_repo: FlagRepository = Depends(get_flag_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    flags, total = await flag_repo.list(
        project_id=project.id,
        offset=offset,
        limit=limit,
        tag=tag,
        search=search,
    )
    return PaginatedResponse(
        items=[FlagResponse.model_validate(f) for f in flags],
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        ),
    )


@router.get("/{flag_key}", response_model=FlagDetailResponse)
async def get_flag(
    project_key: str,
    flag_key: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    flag_repo: FlagRepository = Depends(get_flag_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    flag = await flag_repo.get_detail(project.id, flag_key)
    if not flag:
        raise EntityNotFoundError("Flag", flag_key)
    return flag


@router.patch("/{flag_key}", response_model=FlagResponse)
async def update_flag(
    project_key: str,
    flag_key: str,
    flag_in: FlagUpdate,
    project_repo: ProjectRepository = Depends(get_project_repo),
    flag_repo: FlagRepository = Depends(get_flag_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    flag = await flag_repo.update(project.id, flag_key, flag_in)
    await flag_repo.session.commit()
    await audit_repo.record(
        project_id=project.id,
        entity_type="flag",
        entity_id=str(flag.id),
        action="update",
        actor="system",
        changes=flag_in.model_dump(exclude_unset=True),
    )
    await flag_repo.session.commit()
    refreshed = await flag_repo.get_by_key(project.id, flag_key)
    return refreshed


@router.delete("/{flag_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flag(
    project_key: str,
    flag_key: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    flag_repo: FlagRepository = Depends(get_flag_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    flag = await flag_repo.get_by_key(project.id, flag_key)
    if not flag:
        raise EntityNotFoundError("Flag", flag_key)

    flag_id = flag.id
    await flag_repo.delete(project.id, flag_key)
    await flag_repo.session.commit()
    await audit_repo.record(
        project_id=project.id,
        entity_type="flag",
        entity_id=str(flag_id),
        action="delete",
        actor="system",
        changes={"key": flag_key},
    )
    await flag_repo.session.commit()


@router.get(
    "/{flag_key}/environments/{env_key}",
    response_model=FlagEnvironmentStateResponse,
)
async def get_flag_environment_state(
    project_key: str,
    flag_key: str,
    env_key: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    flag_repo: FlagRepository = Depends(get_flag_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    flag = await flag_repo.get_by_key(project.id, flag_key)
    if not flag:
        raise EntityNotFoundError("Flag", flag_key)

    env = await project_repo.get_environment_by_key(project.id, env_key)
    if not env:
        raise EntityNotFoundError("Environment", env_key)

    state = await flag_repo.get_environment_state(flag.id, env.id)
    if not state:
        raise EntityNotFoundError("FlagEnvironmentState", f"{flag_key}:{env_key}")

    return state


@router.put(
    "/{flag_key}/environments/{env_key}",
    response_model=FlagEnvironmentStateResponse,
)
async def update_flag_environment_state(
    project_key: str,
    flag_key: str,
    env_key: str,
    state_in: FlagEnvironmentStateUpdate,
    project_repo: ProjectRepository = Depends(get_project_repo),
    flag_repo: FlagRepository = Depends(get_flag_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    flag = await flag_repo.get_by_key(project.id, flag_key)
    if not flag:
        raise EntityNotFoundError("Flag", flag_key)

    env = await project_repo.get_environment_by_key(project.id, env_key)
    if not env:
        raise EntityNotFoundError("Environment", env_key)

    state = await flag_repo.update_environment_state(flag.id, env.id, state_in)
    await flag_repo.session.commit()
    await audit_repo.record(
        project_id=project.id,
        entity_type="flag_state",
        entity_id=str(state.id),
        action="update_state",
        actor="system",
        changes=state_in.model_dump(exclude_unset=True),
    )
    await flag_repo.session.commit()
    refreshed = await flag_repo.get_environment_state(flag.id, env.id)
    return refreshed
