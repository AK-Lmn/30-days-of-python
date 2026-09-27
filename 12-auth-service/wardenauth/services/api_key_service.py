from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.core.errors import InsufficientPermissionsError, InvalidApiKeyError
from wardenauth.core.hashing import hash_secret
from wardenauth.core.tokens import generate_api_key_pair
from wardenauth.models.entities import ApiKey
from wardenauth.repositories.api_key_repo import ApiKeyRepo


class ApiKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ApiKeyRepo(session)

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str],
    ) -> tuple[ApiKey, str]:
        prefix, plain_key, key_hash = generate_api_key_pair()
        scopes_str = ",".join(scopes)
        api_key = await self.repo.create(
            user_id=user_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes_str,
        )
        return api_key, plain_key

    async def validate_api_key(self, plain_key: str) -> ApiKey:
        key_hash = hash_secret(plain_key)
        api_key = await self.repo.get_by_hash(key_hash)
        if not api_key or api_key.is_revoked:
            raise InvalidApiKeyError()
        await self.repo.touch(api_key)
        return api_key

    async def list_keys_for_user(self, user_id: str) -> list[ApiKey]:
        return await self.repo.list_by_user(user_id)

    async def revoke_key(
        self,
        key_id: str,
        requesting_user_id: str | None = None,
        is_admin: bool = False,
    ) -> ApiKey:
        api_key = await self.repo.get_by_id(key_id)
        if not api_key:
            raise InvalidApiKeyError("API key not found")
        if not is_admin and requesting_user_id and api_key.user_id != requesting_user_id:
            raise InsufficientPermissionsError("Cannot revoke another user's API key")
        return await self.repo.revoke(api_key)

    async def count_active(self) -> int:
        return await self.repo.count_api_keys()
