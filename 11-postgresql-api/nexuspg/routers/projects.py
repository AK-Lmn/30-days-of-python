from fastapi import APIRouter, Depends, Query, status
from nexuspg.core.errors import EntityNotFoundError
from nexuspg.dependencies import get_audit_repo, get_project_repo
from nexuspg.repositories.audit_repo import AuditRepository
from nexuspg.repositories.project_repo import ProjectRepository
from nexuspg.schemas.common import PaginatedResponse, PaginationMeta
from nexuspg.schemas.project import (
    EnvironmentCreate,
    EnvironmentResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    repo: ProjectRepository = Depends(get_project_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project = await repo.create(project_in)
    await repo.session.commit()
    await audit_repo.record(
        project_id=project.id,
        entity_type="project",
        entity_id=str(project.id),
        action="create",
        actor="system",
        changes=project_in.model_dump(),
    )
    await repo.session.commit()
    refreshed = await repo.get_by_id(project.id)
    return refreshed


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    repo: ProjectRepository = Depends(get_project_repo),
):
    projects, total = await repo.list(offset=offset, limit=limit)
    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        ),
    )


@router.get("/{project_key}", response_model=ProjectResponse)
async def get_project(
    project_key: str,
    repo: ProjectRepository = Depends(get_project_repo),
):
    project = await repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)
    return project


@router.patch("/{project_key}", response_model=ProjectResponse)
async def update_project(
    project_key: str,
    project_in: ProjectUpdate,
    repo: ProjectRepository = Depends(get_project_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project = await repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    updated = await repo.update(project.id, project_in)
    await repo.session.commit()
    await audit_repo.record(
        project_id=project.id,
        entity_type="project",
        entity_id=str(project.id),
        action="update",
        actor="system",
        changes=project_in.model_dump(exclude_unset=True),
    )
    await repo.session.commit()
    refreshed = await repo.get_by_id(project.id)
    return refreshed


@router.delete("/{project_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_key: str,
    repo: ProjectRepository = Depends(get_project_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project = await repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    project_id = project.id
    await repo.delete(project_id)
    await repo.session.commit()
    await audit_repo.record(
        project_id=None,
        entity_type="project",
        entity_id=str(project_id),
        action="delete",
        actor="system",
        changes={"key": project_key},
    )
    await repo.session.commit()


@router.get("/{project_key}/environments", response_model=list[EnvironmentResponse])
async def list_environments(
    project_key: str,
    repo: ProjectRepository = Depends(get_project_repo),
):
    project = await repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)
    return await repo.list_environments(project.id)


@router.post(
    "/{project_key}/environments",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_environment(
    project_key: str,
    env_in: EnvironmentCreate,
    repo: ProjectRepository = Depends(get_project_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project = await repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    env = await repo.create_environment(project.id, env_in)
    await repo.session.commit()
    await audit_repo.record(
        project_id=project.id,
        entity_type="environment",
        entity_id=str(env.id),
        action="create",
        actor="system",
        changes=env_in.model_dump(),
    )
    await repo.session.commit()
    return env


@router.delete(
    "/{project_key}/environments/{env_key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_environment(
    project_key: str,
    env_key: str,
    repo: ProjectRepository = Depends(get_project_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    project = await repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    env = await repo.get_environment_by_key(project.id, env_key)
    if not env:
        raise EntityNotFoundError("Environment", env_key)

    await repo.delete_environment(project.id, env_key)
    await repo.session.commit()
    await audit_repo.record(
        project_id=project.id,
        entity_type="environment",
        entity_id=str(env.id),
        action="delete",
        actor="system",
        changes={"key": env_key},
    )
    await repo.session.commit()
