from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.models.entities import ApiKey


class ApiKeyRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: str,
        name: str,
        key_prefix: str,
        key_hash: str,
        scopes: str = "profile:read",
    ) -> ApiKey:
        api_key = ApiKey(
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes,
        )
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return api_key

    async def get_by_id(self, key_id: str) -> ApiKey | None:
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.id == key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_revoked == False)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[ApiKey]:
        result = await self.session.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, api_key: ApiKey) -> ApiKey:
        api_key.is_revoked = True
        await self.session.commit()
        await self.session.refresh(api_key)
        return api_key

    async def touch(self, api_key: ApiKey) -> None:
        api_key.last_used_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def count_api_keys(self) -> int:
        result = await self.session.execute(
            select(func.count(ApiKey.id)).where(ApiKey.is_revoked == False)
        )
        return result.scalar_one()
