from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.api.deps import get_db
from hookrelay.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionRead,
    SubscriptionUpdate,
)
from hookrelay.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


@router.post("", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionRead:
    subscription = await SubscriptionService.create(db, data)
    return SubscriptionRead.model_validate(subscription)


@router.get("", response_model=list[SubscriptionRead])
async def list_subscriptions(
    active_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[SubscriptionRead]:
    subscriptions = await SubscriptionService.list_all(
        db, active_only=active_only, limit=limit, offset=offset
    )
    return [SubscriptionRead.model_validate(sub) for sub in subscriptions]


@router.get("/{subscription_id}", response_model=SubscriptionRead)
async def get_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionRead:
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription '{subscription_id}' not found",
        )
    return SubscriptionRead.model_validate(subscription)


@router.patch("/{subscription_id}", response_model=SubscriptionRead)
async def update_subscription(
    subscription_id: str,
    data: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionRead:
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription '{subscription_id}' not found",
        )
    updated = await SubscriptionService.update(db, subscription, data)
    return SubscriptionRead.model_validate(updated)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription '{subscription_id}' not found",
        )
    await SubscriptionService.delete(db, subscription)
