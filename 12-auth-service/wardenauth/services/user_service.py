from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.core.errors import UserNotFoundError
from wardenauth.core.permissions import Role
from wardenauth.models.entities import User
from wardenauth.repositories.user_repo import UserRepo


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepo(session)

    async def get_user_by_id(self, user_id: str) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.repo.get_by_email(email)

    async def get_user_by_username(self, username: str) -> User | None:
        return await self.repo.get_by_username(username)

    async def update_profile(self, user_id: str, full_name: str | None) -> User:
        user = await self.get_user_by_id(user_id)
        user.full_name = full_name
        return await self.repo.update(user)

    async def update_role(self, user_id: str, new_role: str) -> User:
        user = await self.get_user_by_id(user_id)
        valid_roles = {r.value for r in Role}
        if new_role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of {valid_roles}")
        user.role = new_role
        return await self.repo.update(user)

    async def update_status(self, user_id: str, new_status: str) -> User:
        user = await self.get_user_by_id(user_id)
        if new_status not in {"active", "suspended"}:
            raise ValueError("Status must be either 'active' or 'suspended'")
        user.status = new_status
        return await self.repo.update(user)

    async def delete_user(self, user_id: str) -> None:
        user = await self.get_user_by_id(user_id)
        await self.repo.delete(user)

    async def list_users(
        self,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        return await self.repo.list_users(offset=offset, limit=limit, search=search)

    async def get_user_stats(self) -> dict[str, int]:
        total = await self.repo.count_users()
        active = await self.repo.count_users_by_status("active")
        suspended = await self.repo.count_users_by_status("suspended")
        return {
            "total_users": total,
            "active_users": active,
            "suspended_users": suspended,
        }
