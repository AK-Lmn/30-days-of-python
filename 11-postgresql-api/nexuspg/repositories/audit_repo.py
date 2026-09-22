from __future__ import annotations
from typing import Any, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from nexuspg.db.models import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        project_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str,
        changes: Optional[Any] = None,
    ) -> AuditLog:
        entry = AuditLog(
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            changes=changes,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list(
        self,
        project_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        if project_id:
            query = query.where(AuditLog.project_id == project_id)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)

        count_stmt = select(func.count(AuditLog.id))
        if project_id:
            count_stmt = count_stmt.where(AuditLog.project_id == project_id)
        if entity_type:
            count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)

        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total
