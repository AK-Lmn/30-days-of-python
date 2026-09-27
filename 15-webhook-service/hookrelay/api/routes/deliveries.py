from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.api.deps import get_db
from hookrelay.schemas.delivery import DeliveryRead, DeliverySummary, ReplayResponse
from hookrelay.services.delivery_service import DeliveryService

router = APIRouter(prefix="/api/v1/deliveries", tags=["Deliveries"])


@router.get("", response_model=list[DeliverySummary])
async def list_deliveries(
    status: str | None = None,
    event_id: str | None = None,
    subscription_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[DeliverySummary]:
    deliveries = await DeliveryService.list_all(
        db,
        status=status,
        event_id=event_id,
        subscription_id=subscription_id,
        limit=limit,
        offset=offset,
    )
    return [DeliverySummary.model_validate(d) for d in deliveries]


@router.get("/{delivery_id}", response_model=DeliveryRead)
async def get_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
) -> DeliveryRead:
    delivery = await DeliveryService.get_by_id(db, delivery_id)
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery '{delivery_id}' not found",
        )
    return DeliveryRead.model_validate(delivery)


@router.post("/{delivery_id}/replay", response_model=ReplayResponse)
async def replay_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReplayResponse:
    try:
        delivery, attempt = await DeliveryService.replay_delivery(db, delivery_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return ReplayResponse(
        delivery_id=delivery.id,
        status=delivery.status,
        attempt_number=attempt.attempt_number if attempt else delivery.attempts_count,
        status_code=attempt.status_code if attempt else None,
        success=delivery.status == "success",
        error_message=attempt.error_message if attempt else None,
    )


@router.post("/process-retries", response_model=list[DeliverySummary])
async def process_retries(
    db: AsyncSession = Depends(get_db),
) -> list[DeliverySummary]:
    processed = await DeliveryService.process_pending_retries(db)
    return [DeliverySummary.model_validate(d) for d in processed]
