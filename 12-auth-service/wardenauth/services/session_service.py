from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.core.errors import InsufficientPermissionsError, SessionNotFoundError, SessionRevokedError
from wardenauth.core.hashing import hash_secret
from wardenauth.models.entities import Session
from wardenauth.repositories.session_repo import SessionRepo


class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = SessionRepo(session)

    async def create_session(
        self,
        user_id: str,
        refresh_token: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> Session:
        token_hash = hash_secret(refresh_token)
        return await self.repo.create(
            user_id=user_id,
            refresh_token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def get_session(self, session_id: str) -> Session:
        sess = await self.repo.get_by_id(session_id)
        if not sess:
            raise SessionNotFoundError()
        return sess

    async def validate_session(self, session_id: str) -> Session:
        sess = await self.get_session(session_id)
        now = datetime.now(timezone.utc)
        if sess.is_revoked:
            raise SessionRevokedError()
        sess_expires = sess.expires_at
        if sess_expires.tzinfo is None:
            sess_expires = sess_expires.replace(tzinfo=timezone.utc)
        if sess_expires <= now:
            raise SessionRevokedError("Session has expired")
        return sess

    async def list_user_sessions(self, user_id: str) -> list[Session]:
        return await self.repo.list_by_user(user_id=user_id)

    async def list_active_sessions(
        self,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Session], int]:
        return await self.repo.list_active(offset=offset, limit=limit)

    async def revoke_session(
        self,
        session_id: str,
        requesting_user_id: str | None = None,
        is_admin: bool = False,
    ) -> Session:
        sess = await self.get_session(session_id)
        if not is_admin and requesting_user_id and sess.user_id != requesting_user_id:
            raise InsufficientPermissionsError("Cannot revoke another user's session")
        return await self.repo.revoke(sess)

    async def revoke_all_sessions(self, user_id: str) -> int:
        return await self.repo.revoke_all_for_user(user_id)

    async def rotate_refresh_token(
        self,
        user_session: Session,
        new_refresh_token: str,
        new_expires_at: datetime,
    ) -> Session:
        new_token_hash = hash_secret(new_refresh_token)
        return await self.repo.update_refresh_token(
            user_session=user_session,
            new_token_hash=new_token_hash,
            expires_at=new_expires_at,
        )

    async def touch(self, user_session: Session) -> None:
        await self.repo.touch(user_session)

    async def count_active(self) -> int:
        return await self.repo.count_active_sessions()
