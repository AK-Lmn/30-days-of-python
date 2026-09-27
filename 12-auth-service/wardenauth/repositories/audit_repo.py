from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.models.entities import AuditLog


class AuditRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        event_type: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def list_logs(
        self,
        offset: int = 0,
        limit: int = 50,
        user_id: str | None = None,
        event_type: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt = select(func.count(AuditLog.id))

        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
            count_stmt = count_stmt.where(AuditLog.user_id == user_id)

        if event_type:
            stmt = stmt.where(AuditLog.event_type == event_type)
            count_stmt = count_stmt.where(AuditLog.event_type == event_type)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        logs = list(result.scalars().all())

        return logs, total

    async def count_recent(self, minutes: int = 60) -> int:
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        result = await self.session.execute(
            select(func.count(AuditLog.id)).where(AuditLog.created_at >= since)
        )
        return result.scalar_one()
