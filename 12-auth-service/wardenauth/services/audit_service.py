import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.models.entities import AuditLog
from wardenauth.repositories.audit_repo import AuditRepo


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AuditRepo(session)

    async def log_event(
        self,
        event_type: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | str | None = None,
    ) -> AuditLog:
        details_str: str | None = None
        if isinstance(details, dict):
            details_str = json.dumps(details)
        elif isinstance(details, str):
            details_str = details

        return await self.repo.create(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details_str,
        )

    async def list_logs(
        self,
        offset: int = 0,
        limit: int = 50,
        user_id: str | None = None,
        event_type: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        return await self.repo.list_logs(
            offset=offset,
            limit=limit,
            user_id=user_id,
            event_type=event_type,
        )

    async def count_recent(self, minutes: int = 60) -> int:
        return await self.repo.count_recent(minutes=minutes)
