from __future__ import annotations
import secrets
from typing import Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from nexuspg.core.errors import EntityAlreadyExistsError, EntityNotFoundError
from nexuspg.db.models import Environment, Flag, FlagEnvironmentState, Project
from nexuspg.schemas.project import EnvironmentCreate, ProjectCreate, ProjectUpdate


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_key(self, key: str) -> Optional[Project]:
        stmt = (
            select(Project)
            .where(Project.key == key)
            .options(selectinload(Project.environments))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.environments))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(self, offset: int = 0, limit: int = 50) -> tuple[list[Project], int]:
        count_stmt = select(func.count(Project.id))
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            select(Project)
            .options(selectinload(Project.environments))
            .order_by(Project.name.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        projects = list(result.scalars().all())
        return projects, total

    async def create(self, project_in: ProjectCreate) -> Project:
        existing = await self.get_by_key(project_in.key)
        if existing:
            raise EntityAlreadyExistsError("Project", "key", project_in.key)

        project = Project(
            key=project_in.key,
            name=project_in.name,
            description=project_in.description,
        )
        self.session.add(project)
        await self.session.flush()

        default_envs = [
            ("development", "Development"),
            ("staging", "Staging"),
            ("production", "Production"),
        ]
        for env_key, env_name in default_envs:
            env = Environment(
                project_id=project.id,
                key=env_key,
                name=env_name,
                api_key=f"env_{secrets.token_hex(20)}",
            )
            self.session.add(env)

        await self.session.flush()
        await self.session.refresh(project, ["environments"])
        return project

    async def update(self, project_id: uuid.UUID, project_in: ProjectUpdate) -> Project:
        project = await self.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        if project_in.name is not None:
            project.name = project_in.name
        if project_in.description is not None:
            project.description = project_in.description

        await self.session.flush()
        await self.session.refresh(project, ["environments"])
        return project

    async def delete(self, project_id: uuid.UUID) -> bool:
        project = await self.get_by_id(project_id)
        if not project:
            return False

        await self.session.delete(project)
        await self.session.flush()
        return True

    async def get_environment_by_key(self, project_id: uuid.UUID, env_key: str) -> Optional[Environment]:
        stmt = select(Environment).where(
            Environment.project_id == project_id,
            Environment.key == env_key,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_environment_by_api_key(self, api_key: str) -> Optional[Environment]:
        stmt = select(Environment).where(Environment.api_key == api_key)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_environments(self, project_id: uuid.UUID) -> list[Environment]:
        stmt = select(Environment).where(Environment.project_id == project_id).order_by(Environment.name.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_environment(self, project_id: uuid.UUID, env_in: EnvironmentCreate) -> Environment:
        project = await self.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        existing = await self.get_environment_by_key(project_id, env_in.key)
        if existing:
            raise EntityAlreadyExistsError("Environment", "key", env_in.key)

        env = Environment(
            project_id=project_id,
            key=env_in.key,
            name=env_in.name,
            api_key=f"env_{secrets.token_hex(20)}",
        )
        self.session.add(env)
        await self.session.flush()

        flags_stmt = select(Flag).where(Flag.project_id == project_id)
        flags_res = await self.session.execute(flags_stmt)
        flags = flags_res.scalars().all()

        for flag in flags:
            state = FlagEnvironmentState(
                flag_id=flag.id,
                environment_id=env.id,
                enabled=False,
                percentage=100,
            )
            self.session.add(state)

        await self.session.flush()
        return env

    async def delete_environment(self, project_id: uuid.UUID, env_key: str) -> bool:
        env = await self.get_environment_by_key(project_id, env_key)
        if not env:
            return False

        await self.session.delete(env)
        await self.session.flush()
        return True
