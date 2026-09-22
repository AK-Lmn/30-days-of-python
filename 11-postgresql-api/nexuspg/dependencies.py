from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from nexuspg.db.session import get_db_session
from nexuspg.repositories.analytics_repo import AnalyticsRepository
from nexuspg.repositories.audit_repo import AuditRepository
from nexuspg.repositories.flag_repo import FlagRepository
from nexuspg.repositories.project_repo import ProjectRepository


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_project_repo(session: AsyncSession = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(session)


def get_flag_repo(session: AsyncSession = Depends(get_db)) -> FlagRepository:
    return FlagRepository(session)


def get_analytics_repo(session: AsyncSession = Depends(get_db)) -> AnalyticsRepository:
    return AnalyticsRepository(session)


def get_audit_repo(session: AsyncSession = Depends(get_db)) -> AuditRepository:
    return AuditRepository(session)
