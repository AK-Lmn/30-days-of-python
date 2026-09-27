from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.api.deps import get_db
from hookrelay.schemas.delivery import DeliverySummary
from hookrelay.schemas.event import EventRead, EventSummary
from hookrelay.services.delivery_service import DeliveryService
from hookrelay.services.event_service import EventService

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


@router.get("", response_model=list[EventSummary])
async def list_events(
    endpoint_id: str | None = None,
    event_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[EventSummary]:
    events = await EventService.list_all(
        db,
        endpoint_id=endpoint_id,
        event_type=event_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [EventSummary.model_validate(evt) for evt in events]


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> EventRead:
    event = await EventService.get_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found",
        )
    return EventRead.model_validate(event)


@router.get("/{event_id}/deliveries", response_model=list[DeliverySummary])
async def get_event_deliveries(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[DeliverySummary]:
    event = await EventService.get_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found",
        )
    deliveries = await DeliveryService.list_all(db, event_id=event_id)
    return [DeliverySummary.model_validate(d) for d in deliveries]
