from datetime import datetime, timezone
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.models.entities import Session


class SessionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, session_id: str) -> Session | None:
        result = await self.session.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_refresh_token_hash(self, token_hash: str) -> Session | None:
        result = await self.session.execute(
            select(Session).where(Session.refresh_token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: str,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> Session:
        user_session = Session(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(user_session)
        await self.session.commit()
        await self.session.refresh(user_session)
        return user_session

    async def list_by_user(
        self,
        user_id: str,
        include_revoked: bool = False,
    ) -> list[Session]:
        stmt = select(Session).where(Session.user_id == user_id)
        if not include_revoked:
            now = datetime.now(timezone.utc)
            stmt = stmt.where(
                Session.is_revoked == False,
                Session.expires_at > now,
            )
        stmt = stmt.order_by(Session.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active(
        self,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Session], int]:
        now = datetime.now(timezone.utc)
        condition = (Session.is_revoked == False) & (Session.expires_at > now)

        count_result = await self.session.execute(
            select(func.count(Session.id)).where(condition)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(Session)
            .where(condition)
            .order_by(Session.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def revoke(self, user_session: Session) -> Session:
        user_session.is_revoked = True
        await self.session.commit()
        await self.session.refresh(user_session)
        return user_session

    async def revoke_all_for_user(self, user_id: str) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Session)
            .where(
                Session.user_id == user_id,
                Session.is_revoked == False,
                Session.expires_at > now,
            )
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def update_refresh_token(
        self,
        user_session: Session,
        new_token_hash: str,
        expires_at: datetime,
    ) -> Session:
        user_session.refresh_token_hash = new_token_hash
        user_session.expires_at = expires_at
        user_session.last_activity_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(user_session)
        return user_session

    async def touch(self, user_session: Session) -> None:
        user_session.last_activity_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def count_active_sessions(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(func.count(Session.id)).where(
                Session.is_revoked == False,
                Session.expires_at > now,
            )
        )
        return result.scalar_one()
