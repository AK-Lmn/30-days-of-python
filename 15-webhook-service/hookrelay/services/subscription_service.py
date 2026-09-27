from typing import Sequence
import fnmatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.models.subscription import Subscription
from hookrelay.schemas.subscription import SubscriptionCreate, SubscriptionUpdate


class SubscriptionService:
    @staticmethod
    async def create(db: AsyncSession, data: SubscriptionCreate) -> Subscription:
        subscription = Subscription(
            name=data.name,
            target_url=str(data.target_url),
            secret_token=data.secret_token or Subscription.secret_token.default.arg(None),
            event_patterns=data.event_patterns,
            is_active=data.is_active,
            max_retries=data.max_retries,
            backoff_base_seconds=data.backoff_base_seconds,
            timeout_seconds=data.timeout_seconds,
        )
        db.add(subscription)
        await db.flush()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def get_by_id(db: AsyncSession, subscription_id: str) -> Subscription | None:
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        return result.scalars().first()

    @staticmethod
    async def list_all(
        db: AsyncSession,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Subscription]:
        stmt = select(Subscription)
        if active_only:
            stmt = stmt.where(Subscription.is_active.is_(True))
        stmt = stmt.order_by(Subscription.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession,
        subscription: Subscription,
        data: SubscriptionUpdate,
    ) -> Subscription:
        update_data = data.model_dump(exclude_unset=True)
        if "target_url" in update_data and update_data["target_url"] is not None:
            update_data["target_url"] = str(update_data["target_url"])
        for field, value in update_data.items():
            setattr(subscription, field, value)
        await db.flush()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def delete(db: AsyncSession, subscription: Subscription) -> None:
        await db.delete(subscription)
        await db.flush()

    @staticmethod
    def matches_event(subscription: Subscription, event_type: str) -> bool:
        if not subscription.is_active:
            return False
        patterns = subscription.event_patterns or ["*"]
        for pattern in patterns:
            if pattern == "*" or pattern == event_type:
                return True
            if fnmatch.fnmatch(event_type, pattern):
                return True
        return False

    @classmethod
    async def get_matching_subscriptions(
        cls,
        db: AsyncSession,
        event_type: str,
    ) -> list[Subscription]:
        all_active = await cls.list_all(db, active_only=True)
        return [sub for sub in all_active if cls.matches_event(sub, event_type)]
